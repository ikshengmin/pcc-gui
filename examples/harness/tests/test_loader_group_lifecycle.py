"""Group disable/re-enable contracts from the pinned Harness Loader."""

import pytest

from loader_runtime import LoaderEntry, PluginCatalog, PluginLoader
from plugin_runtime import PluginKernel


def test_disabled_group_keeps_private_realm_and_joined_consumer_across_hot_update():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []
    events = []

    def provider(scope, config):
        scope.provide("model", "old")
        scope.on("probe", lambda payload: events.append("old"), global_listener=True)

    def replacement(scope, config):
        scope.provide("model", "new")
        scope.on("probe", lambda payload: events.append("new"), global_listener=True)

    def consumer(scope):
        value = scope.require("model", "joined-consumer")
        trace.append("on:" + value)
        scope.effect(lambda: lambda: trace.append("off:" + value))

    catalog.register("provider", provider)
    loader = PluginLoader(kernel, catalog)
    group = LoaderEntry(
        "session", group=True, isolate_names=["model"], isolate_realms=[""],
        children=[LoaderEntry("provider", "provider", provides=["model"])],
    )
    try:
        loader.reconcile([group])
        owner = loader.records[0].context
        realm = owner.service_realm("model")
        joined = kernel.context.isolate("model", realm)
        kernel.install("joined-consumer", consumer, inject=["model"], parent=joined)
        consumer_fiber = kernel.plugin_fibers[-1]
        assert trace == ["on:old"]
        kernel.context.emit("probe", None)
        assert events == ["old"]

        group.disabled = True
        loader.reconcile([group])
        assert kernel.plugin_state("joined-consumer") == "PENDING"
        assert kernel.plugin_fibers == [consumer_fiber]
        assert trace == ["on:old", "off:old"]
        assert kernel.context.event_registrations == []
        disabled_records = loader.records.copy()

        catalog.replace("provider", replacement)
        loader.reconcile([group])
        assert trace == ["on:old", "off:old"]
        group.disabled = False
        loader.reconcile([group])
        assert kernel.plugin_state("joined-consumer") == "ACTIVE"
        assert kernel.plugin_fibers[0] is consumer_fiber
        assert trace == ["on:old", "off:old", "on:new"]
        assert [record.entry.entry_id for record in disabled_records] == ["session"]
        assert disabled_records[0].context is owner and owner.active
        assert owner.service_realm("model") == realm
        assert loader.records[0].context is owner
        assert not loader.records[0].entry.disabled
        assert not kernel.context.has("model")
        kernel.context.emit("probe", None)
        assert events == ["old", "new"]
        assert len(kernel.context.event_registrations) == 1

        loader.reconcile([])
        assert not owner.active
        assert loader.records == []
        assert kernel.context.children == [joined]
        assert kernel.plugin_fibers == [consumer_fiber]
        assert kernel.plugin_state("joined-consumer") == "PENDING"
        assert kernel.context.service_registrations == []
        assert kernel.context.event_registrations == []
        kernel.context.emit("probe", None)
        assert events == ["old", "new"]
    finally:
        loader.dispose()
        kernel.dispose()
    assert trace == ["on:old", "off:old", "on:new", "off:new"]
    assert kernel.context.children == []
    assert kernel.context.service_registrations == []


def test_disabled_ancestor_keeps_nested_groups_and_each_descendant_disable_choice():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def resource(scope, config):
        trace.append("on:" + scope.name)
        scope.effect(lambda: lambda: trace.append("off:" + scope.name))

    catalog.register("resource", resource)
    loader = PluginLoader(kernel, catalog)
    leaf = LoaderEntry("leaf", "resource")
    hidden = LoaderEntry("hidden", "resource", disabled=True)
    inner = LoaderEntry("inner", group=True, children=[leaf, hidden])
    outer = LoaderEntry("outer", group=True, disabled=True, children=[inner])
    try:
        loader.reconcile([outer])
        assert loader.mounted_entries() == ["outer", "inner"]
        outer_owner, inner_owner = [record.context for record in loader.records]
        assert inner_owner.parent is outer_owner
        assert trace == []

        outer.disabled = False
        inner.disabled = True
        loader.reconcile([outer])
        assert loader.mounted_entries() == ["outer", "inner"]
        assert [record.context for record in loader.records] == [outer_owner, inner_owner]
        assert trace == []
        inner.disabled = False
        loader.reconcile([outer])
        assert loader.mounted_entries() == ["outer", "inner", "leaf"]
        assert trace == ["on:leaf"]
        assert loader.records[2].context.parent is inner_owner

        outer.disabled = True
        loader.reconcile([outer])
        assert loader.mounted_entries() == ["outer", "inner"]
        assert [record.context for record in loader.records] == [outer_owner, inner_owner]
        assert trace == ["on:leaf", "off:leaf"]
        loader.reconcile([])
        assert not outer_owner.active and not inner_owner.active
        assert kernel.context.children == []
    finally:
        loader.dispose()
        kernel.dispose()


def test_failed_reenable_retains_disabled_snapshot_and_group_owners_for_retry():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def resource(scope, config):
        trace.append("on:" + scope.name)
        scope.effect(lambda: lambda: trace.append("off:" + scope.name))
        if config.get("fail", False):
            raise RuntimeError("cannot enable child")

    catalog.register("resource", resource)
    loader = PluginLoader(kernel, catalog)
    first = LoaderEntry("first", "resource")
    last = LoaderEntry("last", "resource", {"fail": True})
    group = LoaderEntry("group", group=True, disabled=True, children=[first, last])
    try:
        loader.reconcile([group])
        record = loader.records[0]
        owner = record.context
        snapshot = record.entry
        group.disabled = False
        with pytest.raises(RuntimeError, match="cannot enable child"):
            loader.reconcile([group])
        assert loader.records == [record]
        assert record.context is owner and owner.active
        assert record.entry is snapshot and record.entry.disabled
        assert record.entry.children[1].config == {"fail": True}
        assert owner.children == [] and kernel.installed_plugins() == []
        assert trace == ["on:first", "on:last", "off:last", "off:first"]

        last.config["fail"] = False
        loader.reconcile([group])
        assert loader.records[0] is record and record.context is owner
        assert not record.entry.disabled
        assert record.entry.children[1].config == {"fail": False}
        assert trace[-2:] == ["on:first", "on:last"]
    finally:
        loader.dispose()
        kernel.dispose()
    assert trace[-2:] == ["off:last", "off:first"]


def test_disabling_group_then_later_mount_failure_restores_children_and_metadata():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def resource(scope, config):
        trace.append("on:" + scope.name)
        scope.effect(lambda: lambda: trace.append("off:" + scope.name))
        if config.get("fail", False):
            raise RuntimeError("bad sibling")

    catalog.register("resource", resource)
    loader = PluginLoader(kernel, catalog)
    group = LoaderEntry("group", group=True, children=[LoaderEntry("child", "resource")])
    try:
        loader.reconcile([group])
        record, child_record = loader.records
        owner = record.context
        snapshot = record.entry
        group.disabled = True
        broken = LoaderEntry("broken", "resource", {"fail": True})
        with pytest.raises(RuntimeError, match="bad sibling"):
            loader.reconcile([group, broken])
        assert loader.records == [record, child_record]
        assert record.context is owner and owner.active
        assert record.entry is snapshot and not record.entry.disabled
        assert child_record.context.parent is owner
        assert kernel.plugin_state("child") == "ACTIVE"
        assert trace == ["on:child", "off:child", "on:broken", "off:broken", "on:child"]
    finally:
        loader.dispose()
        kernel.dispose()

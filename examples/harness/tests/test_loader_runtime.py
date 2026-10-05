import json

import pytest

from loader_runtime import (
    Bundle,
    EntryPatch,
    LoaderEntry,
    PluginCatalog,
    PluginLoader,
    ProfileComposer,
    RuntimeProfile,
    apply_patch_layers,
    dump_entry_tree,
)
from plugin_runtime import PluginKernel


def test_patch_layers_replace_insert_and_remove_complete_entries():
    original_child = LoaderEntry("provider", "model", {"value": "v1"})
    original = [LoaderEntry("runtime", group=True, children=[original_child])]
    replacement = LoaderEntry("provider", "model", {"value": "v2"})
    inserted = LoaderEntry("consumer", "consumer", inject=["model"])

    result = apply_patch_layers(
        original,
        [
            [
                EntryPatch("provider", replacement),
                EntryPatch("consumer", inserted, after="provider"),
            ],
            [EntryPatch("consumer", remove=True)],
        ],
    )

    assert original[0].children == [original_child]
    assert len(result[0].children) == 1
    assert result[0].children[0].entry_id == "provider"
    assert result[0].children[0].config == {"value": "v2"}


def test_loader_mounts_consumer_before_provider_in_one_isolated_group():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    seen = []

    def consumer(scope, config) -> None:
        seen.append(config["tag"] + ":" + scope.require("model", "consumer"))

    def provider(scope, config) -> None:
        scope.provide("model", config["value"], config["relationship"])

    catalog.register("consumer", consumer)
    catalog.register("model", provider)
    loader = PluginLoader(kernel, catalog)
    entries = [
        LoaderEntry(
            "session",
            group=True,
            isolate_names=["model"],
            isolate_realms=["session-a"],
            children=[
                LoaderEntry(
                    "consumer",
                    "consumer",
                    {"tag": "active"},
                    inject=["model"],
                ),
                LoaderEntry(
                    "provider",
                    "model",
                    {"value": "deepseek", "relationship": "session-a-model"},
                    provides=["model"],
                ),
            ],
        )
    ]

    loader.reconcile(entries)

    assert loader.mounted_entries() == ["session", "consumer", "provider"]
    assert kernel.plugin_state("consumer") == "ACTIVE"
    assert seen == ["active:deepseek"]
    snapshot = kernel.graph_snapshot()
    assert snapshot["plugins"][0]["inject"][0]["realm"] == "session-a"
    assert snapshot["plugins"][0]["inject"][0]["provider"] == "provider"
    assert not kernel.context.has("model")


def test_loader_incrementally_withdraws_and_restores_provider():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    loads = []
    catalog.register(
        "consumer",
        lambda scope, config: loads.append(scope.require("service", "consumer")),
    )
    catalog.register(
        "provider",
        lambda scope, config: scope.provide("service", config["value"]),
    )
    loader = PluginLoader(kernel, catalog)
    consumer = LoaderEntry("consumer", "consumer", inject=["service"])
    provider = LoaderEntry(
        "provider", "provider", {"value": "v1"}, provides=["service"]
    )

    loader.reconcile([consumer, provider])
    loader.reconcile([consumer])
    assert kernel.plugin_state("consumer") == "PENDING"
    assert loader.mounted_entries() == ["consumer"]

    loader.reconcile([consumer, provider])
    assert kernel.plugin_state("consumer") == "ACTIVE"
    assert loads == ["v1", "v1"]


def test_failed_config_update_rolls_back_previous_stable_suffix():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    events = []

    def configurable(scope, config) -> None:
        value = config["value"]
        events.append("on:" + value)
        scope.effect(lambda: lambda: events.append("off:" + value), "resource")
        if config.get("fail", False):
            raise RuntimeError("bad replacement")
        scope.provide("configured", value)

    catalog.register("configurable", configurable)
    loader = PluginLoader(kernel, catalog)
    stable = LoaderEntry(
        "configured",
        "configurable",
        {"value": "v1"},
        provides=["configured"],
    )
    loader.reconcile([stable])

    with pytest.raises(RuntimeError, match="bad replacement"):
        loader.reconcile(
            [
                LoaderEntry(
                    "configured",
                    "configurable",
                    {"value": "broken", "fail": True},
                    provides=["configured"],
                )
            ]
        )

    assert loader.mounted_entries() == ["configured"]
    assert kernel.context.get("configured") == "v1"
    assert kernel.plugin_state("configured") == "ACTIVE"
    assert events == [
        "on:v1",
        "off:v1",
        "on:broken",
        "off:broken",
        "on:v1",
    ]


def test_loader_orders_static_requirements_and_rejects_cycles_before_mount():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    order = []
    catalog.register("plain", lambda scope, config: order.append(config["name"]))
    loader = PluginLoader(kernel, catalog)

    loader.reconcile(
        [
            LoaderEntry(
                "dependent", "plain", {"name": "dependent"}, requires=["base"]
            ),
            LoaderEntry("base", "plain", {"name": "base"}),
        ]
    )
    assert loader.mounted_entries() == ["base", "dependent"]
    assert order == ["base", "dependent"]

    with pytest.raises(ValueError, match="cycle"):
        PluginLoader(kernel, catalog).reconcile(
            [
                LoaderEntry("left", "plain", requires=["right"]),
                LoaderEntry("right", "plain", requires=["left"]),
            ]
        )


def test_catalog_registration_and_disabled_group_are_owned():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    calls = []
    registration = catalog.register(
        "plain", lambda scope, config: calls.append("mounted")
    )
    loader = PluginLoader(kernel, catalog)
    loader.reconcile(
        [
            LoaderEntry(
                "disabled",
                group=True,
                disabled=True,
                children=[LoaderEntry("hidden", "plain")],
            )
        ]
    )
    assert loader.mounted_entries() == ["disabled"]
    assert calls == []
    assert loader.records[0].context.active
    loader.dispose()
    assert kernel.context.children == []

    registration.dispose()
    registration.dispose()
    with pytest.raises(KeyError, match="not registered"):
        catalog.resolve("plain")


def test_profile_layers_have_explicit_precedence_and_dump_final_tree():
    composer = ProfileComposer()
    base_registration = composer.register_bundle(
        Bundle(
            "base",
            [
                LoaderEntry("core", "core", {"source": "base"}),
                LoaderEntry("telemetry", "telemetry"),
            ],
        )
    )
    composer.register_bundle(
        Bundle(
            "web",
            [
                LoaderEntry("core", "core", {"source": "web-bundle"}),
                LoaderEntry("web", "web", {"source": "bundle"}),
            ],
        )
    )
    profile = RuntimeProfile(
        "web",
        ["base", "web"],
        [EntryPatch("web", LoaderEntry("web", "web", {"source": "profile"}))],
    )

    final_entries = composer.compose(
        profile,
        home_patches=[
            EntryPatch("core", LoaderEntry("core", "core", {"source": "home"}))
        ],
        cli_patches=[
            EntryPatch(
                "user",
                LoaderEntry("user", "user", {"source": "cli"}),
                after="core",
            )
        ],
        launcher_patches=[EntryPatch("telemetry", remove=True)],
    )

    assert [entry.entry_id for entry in final_entries] == ["core", "user", "web"]
    assert final_entries[0].config == {"source": "home"}
    assert final_entries[1].config == {"source": "cli"}
    assert final_entries[2].config == {"source": "profile"}
    dumped = json.loads(dump_entry_tree(final_entries))
    assert [entry["id"] for entry in dumped] == ["core", "user", "web"]
    assert dumped[2]["config"] == {"source": "profile"}

    base_registration.dispose()
    with pytest.raises(KeyError, match="not registered"):
        composer.compose(RuntimeProfile("headless", ["base"]))


def test_catalog_replacement_reloads_same_entry_and_old_disposer_is_stale():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def version_one(scope, config):
        trace.append("v1-on")
        scope.effect(lambda: lambda: trace.append("v1-off"))
        scope.provide("value", "v1")

    def version_two(scope, config):
        trace.append("v2-on")
        scope.effect(lambda: lambda: trace.append("v2-off"))
        scope.provide("value", "v2")

    old = catalog.register("provider", version_one)
    loader = PluginLoader(kernel, catalog)
    entries = [LoaderEntry("provider", "provider", provides=["value"])]
    loader.reconcile(entries)
    replacement = catalog.replace("provider", version_two)
    old.dispose()
    assert catalog.resolve("provider") is version_two
    loader.reconcile(entries)
    assert kernel.context.get("value") == "v2"
    loader.reconcile(entries)
    assert trace == ["v1-on", "v1-off", "v2-on"]
    loader.dispose()
    assert trace == ["v1-on", "v1-off", "v2-on", "v2-off"]
    replacement.dispose()
    with pytest.raises(KeyError):
        catalog.resolve("provider")


def test_failed_hot_replacement_restores_captured_old_implementation():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def stable(scope, config):
        trace.append("stable-on")
        scope.provide("value", "stable")
        scope.effect(lambda: lambda: trace.append("stable-off"))

    def broken(scope, config):
        trace.append("broken-on")
        scope.effect(lambda: lambda: trace.append("broken-off"))
        raise RuntimeError("candidate failed")

    catalog.register("provider", stable)
    loader = PluginLoader(kernel, catalog)
    entries = [LoaderEntry("provider", "provider", provides=["value"])]
    loader.reconcile(entries)
    catalog.replace("provider", broken)
    with pytest.raises(RuntimeError, match="candidate failed"):
        loader.reconcile(entries)
    assert kernel.context.get("value") == "stable"
    assert loader.mounted_entries() == ["provider"]
    assert trace == ["stable-on", "stable-off", "broken-on", "broken-off", "stable-on"]
    loader.dispose()
    assert trace[-1] == "stable-off"


def test_in_place_nested_config_edit_is_detected_and_rollback_uses_snapshot():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def configured(scope, config):
        value = config["nested"]["value"]
        trace.append(value)
        if value == "broken":
            raise RuntimeError("config failed")
        scope.provide("value", value)

    catalog.register("configured", configured)
    entry = LoaderEntry("configured", "configured", {"nested": {"value": "one"}})
    loader = PluginLoader(kernel, catalog)
    loader.reconcile([entry])
    entry.config["nested"]["value"] = "two"
    loader.reconcile([entry])
    assert kernel.context.get("value") == "two"
    entry.config["nested"]["value"] = "broken"
    with pytest.raises(RuntimeError, match="config failed"):
        loader.reconcile([entry])
    assert kernel.context.get("value") == "two"
    assert trace == ["one", "two", "broken", "two"]
    assert loader.records[0].entry.config == {"nested": {"value": "two"}}
    loader.dispose()


def test_failed_old_cleanup_does_not_leave_phantom_committed_entries():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def cleanup():
        trace.append("off")
        raise RuntimeError("old cleanup failed")

    def plugin(scope, config):
        trace.append("on:" + config["value"])
        scope.provide("value", config["value"])
        scope.effect(lambda: cleanup)

    catalog.register("configured", plugin)
    loader = PluginLoader(kernel, catalog)
    first = LoaderEntry("configured", "configured", {"value": "one"})
    loader.reconcile([first])
    second = LoaderEntry("configured", "configured", {"value": "two"})
    with pytest.raises(RuntimeError, match="old cleanup failed"):
        loader.reconcile([second])
    assert loader.mounted_entries() == []
    assert not kernel.context.has("value")
    # Returning to the original desired tree must remount it, not compare
    # equal to an old record whose resources have already been retired.
    loader.reconcile([first])
    assert loader.mounted_entries() == ["configured"]
    assert kernel.context.get("value") == "one"
    assert trace == ["on:one", "off", "on:one"]
    with pytest.raises(RuntimeError, match="old cleanup failed"):
        loader.dispose()


def _tracked_loader():
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def tracked(scope, config):
        label = config["label"]
        trace.append("on:" + label)
        scope.effect(lambda: lambda: trace.append("off:" + label))
        if config.get("fail", False):
            raise RuntimeError("bad replacement")

    catalog.register("tracked", tracked)
    return kernel, catalog, PluginLoader(kernel, catalog), trace


def _tracked_entry(name, label=None, **options):
    return LoaderEntry(name, "tracked", {"label": name if label is None else label}, **options)


def test_keyed_edit_preserves_unrelated_later_scope_and_effects():
    kernel, catalog, loader, trace = _tracked_loader()
    first = _tracked_entry("first")
    later = _tracked_entry("later")
    loader.reconcile([first, later])
    stable = loader.records[1]
    stable_scope = stable.context

    loader.reconcile([_tracked_entry("first", "changed"), later])

    assert loader.records[1] is stable
    assert stable.context is stable_scope
    assert stable_scope.active
    assert trace == ["on:first", "on:later", "off:first", "on:changed"]
    loader.dispose()
    assert trace[-2:] == ["off:later", "off:changed"]


def test_prepend_remove_and_reorder_keep_existing_keyed_instances():
    kernel, catalog, loader, trace = _tracked_loader()
    first = _tracked_entry("first")
    later = _tracked_entry("later")
    loader.reconcile([first, later])
    first_record, later_record = loader.records

    loader.reconcile([_tracked_entry("new"), later, first])
    assert loader.mounted_entries() == ["new", "later", "first"]
    assert loader.records[1] is later_record
    assert loader.records[2] is first_record
    assert trace == ["on:first", "on:later", "on:new"]

    loader.reconcile([later, first])
    assert loader.records == [later_record, first_record]
    assert trace == ["on:first", "on:later", "on:new", "off:new"]
    loader.dispose()
    loader.dispose()
    assert trace[-2:] == ["off:first", "off:later"]


def test_group_replacement_restarts_descendants_but_not_other_group():
    kernel, catalog, loader, trace = _tracked_loader()
    child = _tracked_entry("child")
    first = LoaderEntry("first", group=True, children=[child],
                        isolate_names=["service"], isolate_realms=["one"])
    other = LoaderEntry("other", group=True, children=[_tracked_entry("unrelated")])
    loader.reconcile([first, other])
    old_group, old_child, stable_group, stable_child = loader.records

    replacement = LoaderEntry("first", group=True, children=[child],
                              isolate_names=["service"], isolate_realms=["two"])
    loader.reconcile([replacement, other])

    assert loader.records[2:] == [stable_group, stable_child]
    assert old_group.context is None
    assert old_child.context is None
    assert loader.records[1].context.service_realm("service") == "two"
    assert trace == ["on:child", "on:unrelated", "off:child", "on:child"]
    loader.dispose()


def test_moving_child_changes_parent_without_restarting_other_entries():
    kernel, catalog, loader, trace = _tracked_loader()
    child = _tracked_entry("child")
    left = LoaderEntry("left", group=True, children=[child])
    right = LoaderEntry("right", group=True, children=[_tracked_entry("stable")])
    loader.reconcile([left, right])
    left_record, old_child, right_record, stable_record = loader.records
    previous_scope = old_child.context

    loader.reconcile([
        LoaderEntry("left", group=True),
        LoaderEntry("right", group=True, children=[child, _tracked_entry("stable")]),
    ])

    assert loader.records[0] is left_record
    assert loader.records[1] is right_record
    assert loader.records[3] is stable_record
    assert loader.records[2].context.parent is right_record.context
    assert not previous_scope.active
    assert trace == ["on:child", "on:stable", "off:child", "on:child"]
    loader.dispose()


def test_static_dependency_restart_closure_excludes_unrelated_entries():
    kernel, catalog, loader, trace = _tracked_loader()
    entries = [
        _tracked_entry("base"),
        _tracked_entry("middle", requires=["base"]),
        _tracked_entry("leaf", requires=["middle"]),
        _tracked_entry("stable"),
    ]
    loader.reconcile(entries)
    stable = loader.records[3]

    loader.reconcile([_tracked_entry("base", "new-base"), *entries[1:]])

    assert loader.records[3] is stable
    assert trace == [
        "on:base", "on:middle", "on:leaf", "on:stable",
        "off:leaf", "off:middle", "off:base",
        "on:new-base", "on:middle", "on:leaf",
    ]
    loader.dispose()


def test_hot_replacement_keeps_injected_fiber_and_unrelated_scope():
    kernel, catalog, loader, trace = _tracked_loader()

    def provider(scope, config):
        scope.provide("value", "old")

    def consumer(scope, config):
        value = scope.require("value", "consumer")
        trace.append("consume:" + value)
        scope.effect(lambda: lambda: trace.append("release:" + value))

    catalog.register("provider", provider)
    catalog.register("consumer", consumer)
    entries = [LoaderEntry("provider", "provider", provides=["value"]),
               LoaderEntry("consumer", "consumer", inject=["value"]),
               _tracked_entry("stable")]
    loader.reconcile(entries)
    consumer_record, stable_record = loader.records[1:]
    consumer_fiber = next(fiber for fiber in kernel.plugin_fibers if fiber.name == "consumer")
    catalog.replace("provider", lambda scope, config: scope.provide("value", "new"))

    loader.reconcile(entries)

    assert loader.records[1:] == [consumer_record, stable_record]
    assert next(fiber for fiber in kernel.plugin_fibers if fiber.name == "consumer") is consumer_fiber
    assert trace == ["consume:old", "on:stable", "release:old", "consume:new"]
    loader.dispose()


def test_failed_keyed_update_restores_old_order_and_keeps_unaffected_mount():
    kernel, catalog, loader, trace = _tracked_loader()
    first, stable, last = [_tracked_entry(name) for name in ["first", "stable", "last"]]
    loader.reconcile([first, stable, last])
    stable_record = loader.records[1]
    broken = LoaderEntry("last", "tracked", {"label": "broken", "fail": True})

    with pytest.raises(RuntimeError, match="bad replacement"):
        loader.reconcile([stable, _tracked_entry("first", "changed"), _tracked_entry("new"), broken])

    assert loader.mounted_entries() == ["first", "stable", "last"]
    assert loader.records[1] is stable_record
    assert stable_record.context.active
    assert trace == [
        "on:first", "on:stable", "on:last", "off:last", "off:first",
        "on:changed", "on:new", "on:broken", "off:broken", "off:new", "off:changed",
        "on:first", "on:last",
    ]
    loader.dispose()


def test_cleanup_failure_retires_only_affected_records_before_retry():
    kernel, catalog, loader, trace = _tracked_loader()
    cleanup_calls = []

    def cleanup():
        cleanup_calls.append("off")
        if len(cleanup_calls) == 1:
            raise RuntimeError("cleanup failed once")

    def fragile(scope, config):
        scope.effect(lambda: cleanup)

    catalog.register("fragile", fragile)
    first = LoaderEntry("first", "fragile")
    stable = _tracked_entry("stable")
    loader.reconcile([first, stable])
    stable_record = loader.records[1]
    changed = LoaderEntry("first", "fragile", {"revision": 2})

    with pytest.raises(RuntimeError, match="cleanup failed once"):
        loader.reconcile([changed, stable])
    assert loader.records == [stable_record]
    assert kernel.installed_plugins() == ["stable"]
    assert trace == ["on:stable"]

    loader.reconcile([first, stable])
    assert loader.records[1] is stable_record
    assert loader.mounted_entries() == ["first", "stable"]
    loader.dispose()
    assert cleanup_calls == ["off", "off"]


def test_disabling_group_preserves_unrelated_later_mount():
    kernel, catalog, loader, trace = _tracked_loader()
    group = LoaderEntry("group", group=True, children=[_tracked_entry("child")])
    stable = _tracked_entry("stable")
    loader.reconcile([group, stable])
    group_record = loader.records[0]
    group_scope = group_record.context
    stable_record = loader.records[2]

    group.disabled = True
    loader.reconcile([group, stable])
    assert loader.records == [group_record, stable_record]
    assert group_record.context is group_scope and group_scope.active
    assert group_record.entry.disabled
    assert trace == ["on:child", "on:stable", "off:child"]
    group.disabled = False
    loader.reconcile([group, stable])
    assert loader.records[0] is group_record
    assert group_record.context is group_scope
    assert not group_record.entry.disabled
    assert loader.records[2] is stable_record
    assert trace == ["on:child", "on:stable", "off:child", "on:child"]
    loader.dispose()


def test_rollback_failure_still_restores_independent_changed_entries():
    kernel, catalog, loader, trace = _tracked_loader()
    attempts = []

    def once(scope, config):
        attempts.append(config["label"])
        if len(attempts) > 1:
            raise RuntimeError("old plugin cannot restart")

    catalog.register("once", once)
    first = LoaderEntry("first", "once", {"label": "original"})
    stable, last = _tracked_entry("stable"), _tracked_entry("last")
    loader.reconcile([first, stable, last])
    stable_record = loader.records[1]

    with pytest.raises(RuntimeError, match="rollback did not restore the tree"):
        loader.reconcile([
            LoaderEntry("first", "once", {"label": "candidate"}), stable,
            _tracked_entry("last", "changed"),
        ])

    assert loader.mounted_entries() == ["stable", "last"]
    assert loader.records[0] is stable_record
    assert kernel.plugin_state("first") == "ABSENT"
    assert kernel.plugin_state("last") == "ACTIVE"
    assert attempts == ["original", "candidate", "original"]
    assert trace == ["on:stable", "on:last", "off:last", "on:last"]
    loader.dispose()


def test_candidate_cleanup_failure_is_reported_after_restoring_old_tree():
    kernel, catalog, loader, trace = _tracked_loader()

    def cleanup():
        raise RuntimeError("candidate cleanup broke")

    def candidate(scope, config):
        scope.effect(lambda: cleanup)

    catalog.register("candidate", candidate)
    first, stable = _tracked_entry("first"), _tracked_entry("stable")
    loader.reconcile([first, stable])
    stable_record = loader.records[1]

    with pytest.raises(RuntimeError, match="candidate cleanup broke"):
        loader.reconcile([
            LoaderEntry("first", "candidate"), stable,
            LoaderEntry("broken", "tracked", {"label": "broken", "fail": True}),
        ])

    assert loader.mounted_entries() == ["first", "stable"]
    assert loader.records[1] is stable_record
    assert trace == ["on:first", "on:stable", "off:first", "on:broken", "off:broken", "on:first"]
    loader.dispose()


def test_native_loader_workload_host_oracle(capsys):
    from pathlib import Path
    import runpy

    source = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "harness_loader_keyed.py"
    workload = runpy.run_path(str(source))
    assert workload["main"]() == 0
    assert capsys.readouterr().out == "HARNESS_KEYED_LOADER_OK\n"

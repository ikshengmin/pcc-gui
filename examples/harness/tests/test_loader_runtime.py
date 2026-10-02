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
    assert loader.mounted_entries() == []
    assert calls == []

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

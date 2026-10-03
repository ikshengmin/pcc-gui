"""Native acceptance workload importing the actual Harness Loader and kernel."""

from loader_runtime import LoaderEntry, PluginCatalog, PluginLoader
from plugin_runtime import PluginKernel


def require(condition, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def keyed_lifecycle() -> None:
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def tracked(scope, config):
        label = config["label"]
        trace.append("on:" + label)
        scope.effect(lambda: lambda: trace.append("off:" + label))
        if config.get("fail", False):
            raise RuntimeError("candidate failed")

    catalog.register("tracked", tracked)
    loader = PluginLoader(kernel, catalog)
    first = LoaderEntry("first", "tracked", {"label": "first"})
    stable = LoaderEntry("stable", "tracked", {"label": "stable"})
    loader.reconcile([first, stable])
    original_first = loader.records[0]
    original_stable = loader.records[1]
    loader.reconcile([stable, first])
    require(loader.records[0] is original_stable, "reorder lost stable identity")
    require(loader.records[1] is original_first, "reorder lost first identity")
    require(trace == ["on:first", "on:stable"], "reorder restarted effects")

    changed = LoaderEntry("first", "tracked", {"label": "changed"})
    loader.reconcile([changed, stable])
    require(loader.records[1] is original_stable, "edit restarted unrelated scope")
    require(trace == ["on:first", "on:stable", "off:first", "on:changed"], "edit trace")
    broken = LoaderEntry("first", "tracked", {"label": "broken", "fail": True})
    failed = False
    try:
        loader.reconcile([stable, broken])
    except RuntimeError as error:
        failed = str(error) == "candidate failed"
    require(failed, "failed replacement was not propagated")
    require(loader.mounted_entries() == ["first", "stable"], "rollback order")
    require(loader.records[1] is original_stable, "rollback restarted unrelated scope")
    require(loader.records[0].entry.config["label"] == "changed", "rollback config")
    loader.dispose()
    loader.dispose()
    require(trace == ["on:first", "on:stable", "off:first", "on:changed",
                      "off:changed", "on:broken", "off:broken", "on:changed",
                      "off:stable", "off:changed"], "rollback and disposal trace")


def group_and_dependency_lifecycle() -> None:
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def tracked(scope, config):
        label = config["label"]
        trace.append("on:" + label)
        scope.effect(lambda: lambda: trace.append("off:" + label))

    catalog.register("tracked", tracked)
    loader = PluginLoader(kernel, catalog)
    base = LoaderEntry("base", "tracked", {"label": "base"})
    child = LoaderEntry("child", "tracked", {"label": "child"}, requires=["base"])
    stable = LoaderEntry("stable", "tracked", {"label": "stable"})
    group = LoaderEntry("group", group=True, children=[base, child],
                        isolate_names=["service"], isolate_realms=["one"])
    loader.reconcile([group, stable])
    stable_record = loader.records[3]
    replacement = LoaderEntry("group", group=True, children=[base, child],
                              isolate_names=["service"], isolate_realms=["two"])
    loader.reconcile([replacement, stable])
    require(loader.records[3] is stable_record, "group edit restarted unrelated scope")
    require(loader.records[1].context.service_realm("service") == "two", "group realm")
    require(trace == ["on:base", "on:child", "on:stable", "off:child", "off:base",
                      "on:base", "on:child"], "group dependency trace")
    loader.dispose()


def provider_lifecycle() -> None:
    kernel = PluginKernel()
    catalog = PluginCatalog()
    trace = []

    def provider(scope, config):
        scope.provide("value", "old")

    def consumer(scope, config):
        value = scope.require("value", "consumer")
        trace.append("on:" + value)
        scope.effect(lambda: lambda: trace.append("off:" + value))

    original = catalog.register("provider", provider)
    catalog.register("consumer", consumer)
    loader = PluginLoader(kernel, catalog)
    entries = [LoaderEntry("provider", "provider", provides=["value"]),
               LoaderEntry("consumer", "consumer", inject=["value"])]
    loader.reconcile(entries)
    consumer_record = loader.records[1]
    consumer_fiber = kernel.plugin_fibers[1]
    catalog.replace("provider", lambda scope, config: scope.provide("value", "new"))
    original.dispose()
    loader.reconcile(entries)
    require(loader.records[1] is consumer_record, "provider edit replaced consumer record")
    require(kernel.plugin_fibers[0] is consumer_fiber, "provider edit replaced consumer fiber")
    require(trace == ["on:old", "off:old", "on:new"], "provider transition")
    loader.dispose()
    require(trace == ["on:old", "off:old", "on:new", "off:new"], "provider cleanup")


def registry_release_lifecycle() -> None:
    kernel = PluginKernel()
    catalog = PluginCatalog()
    closed = []

    def resource(scope, config):
        generation = config["generation"]
        scope.effect(lambda: lambda: closed.append(generation))
        scope.provide("value", generation)
        scope.on("change", lambda payload: generation)

    catalog.register("resource", resource)
    loader = PluginLoader(kernel, catalog)
    generation = 0
    while generation < 20:
        loader.reconcile([LoaderEntry("group", group=True, children=[
            LoaderEntry("resource", "resource", {"generation": generation}),
        ])])
        require(len(kernel.context.children) == 1, "retired group retained")
        require(len(kernel.context.children[0].children) == 1, "retired scope retained")
        require(len(kernel.context.service_registrations) == 1, "retired service retained")
        require(len(kernel.context.event_registrations) == 1, "retired listener retained")
        require(len(closed) == generation, "reload cleanup count")
        generation += 1
    loader.dispose()
    require(len(closed) == 20, "final cleanup count")
    require(kernel.context.children == [], "disposed group retained")
    require(kernel.context.service_registrations == [], "disposed services retained")
    require(kernel.context.event_registrations == [], "disposed listeners retained")

    trace = []
    holders = []

    def first(payload):
        trace.append("first")
        holders[0].dispose()

    listener = kernel.context.on("change", first)
    holders.append(kernel.context.on("change", lambda payload: trace.append("second")))
    kernel.context.emit("change", None)
    require(trace == ["first", "second"], "dispatch snapshot changed during unregister")
    require(holders[0].callback is None, "disposed callback retained")
    listener.dispose()
    require(kernel.context.effects == [], "disposed effects retained")
    kernel.dispose()


def main() -> int:
    keyed_lifecycle()
    group_and_dependency_lifecycle()
    provider_lifecycle()
    registry_release_lifecycle()
    print("HARNESS_KEYED_LOADER_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

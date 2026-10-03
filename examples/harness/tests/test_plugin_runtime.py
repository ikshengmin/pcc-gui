import pytest

from plugin_runtime import PluginKernel


def test_scoped_services_override_and_dispose_to_parent():
    kernel = PluginKernel()
    kernel.context.provide("model", "global")
    child = kernel.context.isolate("model")
    registration = child.provide("model", "scoped", "agent-1")

    assert child.get("model") == "scoped"
    assert child.service_relationship("model") == "agent-1"
    assert kernel.context.get("model") == "global"

    registration.dispose()
    assert not child.has("model")
    assert kernel.context.get("model") == "global"
    assert registration.active is False


def test_events_are_visible_to_registration_scope_descendants_only():
    kernel = PluginKernel()
    left = kernel.context.child("left")
    right = kernel.context.child("right")
    seen = []
    kernel.context.on("change", lambda value: seen.append("root:" + value))
    left.on("change", lambda value: seen.append("left:" + value))

    left.emit("change", "a")
    right.emit("change", "b")

    assert seen == ["root:a", "left:a", "root:b"]


def test_disposal_is_reverse_order_and_idempotent():
    kernel = PluginKernel()
    scope = kernel.context.child("plugin")
    disposed = []
    scope.effect(lambda: lambda: disposed.append("first"))
    scope.effect(lambda: lambda: disposed.append("second"))

    scope.dispose()
    scope.dispose()

    assert disposed == ["second", "first"]
    with pytest.raises(RuntimeError, match="disposed"):
        scope.get("anything")


def test_waterfall_requires_explicit_delegation():
    kernel = PluginKernel()
    kernel.context.on(
        "policy", lambda value, next_: next_(value + "-a") + "-after", "waterfall"
    )
    kernel.context.on("policy", lambda value, next_: "blocked:" + value, "waterfall")

    result = kernel.context.waterfall("policy", "start", lambda value: value + "-body")

    assert result == "blocked:start-a-after"


def test_install_rolls_back_effects_when_plugin_raises():
    kernel = PluginKernel()
    disposed = []

    def broken(scope):
        scope.effect(lambda: lambda: disposed.append("rolled-back"))
        scope.provide("partial", object())
        raise RuntimeError("load failed")

    with pytest.raises(RuntimeError, match="load failed"):
        kernel.install("broken", broken)

    assert disposed == ["rolled-back"]
    assert not kernel.context.has("partial")


def test_joined_service_realms_share_provider_without_leaking_to_root():
    kernel = PluginKernel()
    left = kernel.context.isolate("fs", "workspace-a")
    right = kernel.context.isolate("fs", "workspace-a")
    other = kernel.context.isolate("fs", "workspace-b")
    left.provide("fs", "private")

    assert right.get("fs") == "private"
    assert not other.has("fs")
    assert not kernel.context.has("fs")


def test_effect_setup_runs_now_and_cleanup_continues_after_failure():
    kernel = PluginKernel()
    scope = kernel.context.child("owned")
    events = []

    def setup():
        events.append("setup")

        def fail():
            events.append("fail")
            raise RuntimeError("cleanup failed")

        return [lambda: events.append("first"), fail]

    scope.effect(setup)
    scope.effect(lambda: lambda: events.append("last"))
    assert events == ["setup"]

    with pytest.raises(RuntimeError, match="cleanup failed"):
        scope.dispose()
    assert events == ["setup", "last", "fail", "first"]


def test_generator_effect_collects_and_rolls_back_yielded_disposers():
    kernel = PluginKernel()
    scope = kernel.context.child("generator-effect")
    events = []

    def setup():
        events.append("setup")
        yield lambda: events.append("first-off")
        yield lambda: events.append("second-off")
        raise RuntimeError("generator setup failed")

    with pytest.raises(RuntimeError, match="generator setup failed"):
        scope.effect(setup)

    assert events == ["setup", "second-off", "first-off"]
    assert scope.effects == []


def test_invalid_generator_effect_value_rolls_back_prior_disposers():
    kernel = PluginKernel()
    scope = kernel.context.child("invalid-generator-effect")
    events = []

    def setup():
        yield lambda: events.append("released")
        yield "not-a-disposer"

    with pytest.raises(TypeError, match="invalid effect disposer"):
        scope.effect(setup)

    assert events == ["released"]
    assert scope.effects == []


def test_reentrant_owner_disposal_observes_effect_during_setup():
    kernel = PluginKernel()
    scope = kernel.context.child("reentrant")
    events = []

    def setup():
        events.append("setup-start")
        scope.dispose()
        events.append("setup-finish")
        return lambda: events.append("cleanup")

    effect = scope.effect(setup)

    assert events == ["setup-start", "setup-finish", "cleanup"]
    assert effect.active is False
    assert scope.active is False


def test_cleanup_cannot_register_a_new_effect_on_unloading_owner():
    kernel = PluginKernel()
    scope = kernel.context.child("unloading")
    errors = []

    def cleanup():
        try:
            scope.effect(lambda: lambda: None)
        except RuntimeError as error:
            errors.append(str(error))

    scope.effect(lambda: cleanup)
    scope.dispose()

    assert len(errors) == 1
    assert "disposed" in errors[0]
    assert scope.effects == []


def test_disposal_unlinks_scopes_services_listeners_and_releases_resources():
    import gc
    import weakref

    class Resource:
        pass

    kernel = PluginKernel()

    def install_resource():
        resource = Resource()
        scope = kernel.context.child("owned")
        scope.provide("resource", resource)
        scope.on("resource", lambda payload: resource)
        scope.effect(lambda: lambda: resource)
        return weakref.ref(resource), weakref.ref(scope), scope

    resource_ref, scope_ref, scope = install_resource()
    scope.dispose()
    assert kernel.context.children == []
    assert kernel.context.service_registrations == []
    assert kernel.context.event_registrations == []
    assert scope.effects == []
    del scope
    gc.collect()
    assert scope_ref() is None
    assert resource_ref() is None


def test_manual_effect_and_listener_disposal_release_owner_entries():
    kernel = PluginKernel()
    trace = []
    effect = kernel.context.effect(lambda: lambda: trace.append("cleanup"))
    listener = kernel.context.on("change", lambda payload: trace.append("event"))
    service = kernel.context.provide("value", "service")

    effect.dispose()
    effect.dispose()
    listener.dispose()
    service.dispose()

    assert trace == ["cleanup"]
    assert effect.disposers == []
    assert listener.callback is None
    assert kernel.context.effects == []
    assert kernel.context.service_registrations == []
    assert kernel.context.event_registrations == []


def test_repeated_loader_replacement_keeps_only_live_registry_entries():
    from loader_runtime import LoaderEntry, PluginCatalog, PluginLoader

    kernel = PluginKernel()
    catalog = PluginCatalog()
    closed = []

    def plugin(scope, config):
        generation = config["generation"]
        scope.effect(lambda: lambda: closed.append(generation))
        scope.provide("value", generation)
        scope.on("change", lambda payload: generation)

    catalog.register("resource", plugin)
    loader = PluginLoader(kernel, catalog)
    for generation in range(25):
        loader.reconcile([LoaderEntry("group", group=True, children=[
            LoaderEntry("resource", "resource", {"generation": generation}),
        ])])
        assert len(kernel.context.children) == 1
        group = kernel.context.children[0]
        assert len(group.children) == 1
        assert len(kernel.context.service_registrations) == 1
        assert len(kernel.context.event_registrations) == 1
        assert group.children[0].get("value") == generation
        assert closed == list(range(generation))
    loader.dispose()
    assert closed == list(range(25))
    assert kernel.context.children == []
    assert kernel.context.service_registrations == []
    assert kernel.context.event_registrations == []


def test_failed_plugin_setup_leaves_no_retired_registry_entries():
    kernel = PluginKernel()
    closed = []

    def broken(scope):
        scope.effect(lambda: lambda: closed.append("resource"))
        scope.provide("partial", object())
        scope.on("partial", lambda payload: None)
        raise RuntimeError("setup failed")

    for attempt in range(10):
        with pytest.raises(RuntimeError, match="setup failed"):
            kernel.install("broken", broken)
        assert kernel.installed_plugins() == []
        assert kernel.context.children == []
        assert kernel.context.effects == []
        assert kernel.context.service_registrations == []
        assert kernel.context.event_registrations == []
    assert closed == ["resource"] * 10


def test_cleanup_failure_still_unlinks_every_child_and_registration():
    kernel = PluginKernel()
    parent = kernel.context.child("parent")
    child = parent.child("child")
    trace = []

    def fail():
        trace.append("failure")
        raise RuntimeError("cleanup failed")

    parent.effect(lambda: lambda: trace.append("parent"))
    child.provide("value", "old")
    child.on("change", lambda payload: None)
    effect = child.effect(lambda: [lambda: trace.append("first"), fail])
    with pytest.raises(RuntimeError, match="cleanup failed"):
        parent.dispose()

    assert trace == ["failure", "first", "parent"]
    assert parent.children == []
    assert parent.effects == child.effects == effect.disposers == []
    assert kernel.context.children == []
    assert kernel.context.service_registrations == []
    assert kernel.context.event_registrations == []
    parent.dispose()
    assert trace == ["failure", "first", "parent"]


def test_reentrant_sibling_disposal_does_not_skip_child_cleanup():
    kernel = PluginKernel()
    left = kernel.context.child("left")
    middle = kernel.context.child("middle")
    right = kernel.context.child("right")
    trace = []
    left.effect(lambda: lambda: trace.append("left"))
    middle.effect(lambda: lambda: trace.append("middle"))

    def right_cleanup():
        trace.append("right")
        left.dispose()

    right.effect(lambda: right_cleanup)
    kernel.dispose()
    assert trace == ["right", "left", "middle"]
    assert kernel.context.children == []


def test_provider_withdrawal_preserves_committed_value_until_consumer_cleanup():
    kernel = PluginKernel()
    trace = []

    def provider(scope):
        scope.effect(lambda: lambda: trace.append("provider-close"))
        scope.provide("value", "usable")

    def consumer(scope):
        scope.effect(lambda: lambda: trace.append("consumer:" + scope.require("value")))

    kernel.install("provider", provider)
    kernel.install("consumer", consumer, inject=["value"])
    kernel.unload("provider")
    assert trace == ["consumer:usable", "provider-close"]
    assert kernel.plugin_state("consumer") == "PENDING"
    assert kernel.context.children == []
    assert kernel.context.service_registrations == []
    kernel.dispose()


def test_reentrant_withdrawal_keeps_value_until_deferred_kernel_reconciliation():
    kernel = PluginKernel()
    value = kernel.context.provide("value", "usable")
    trace = []

    def consumer(scope):
        trace.append("start:" + scope.require("value"))
        scope.effect(lambda: lambda: trace.append("cleanup:" + scope.require("value")))
        value.dispose()

    kernel.install("consumer", consumer, inject=["value", "trigger"])
    trigger = kernel.context.provide("trigger", True)
    assert trace == ["start:usable", "cleanup:usable"]
    assert kernel.plugin_state("consumer") == "PENDING"
    assert kernel.context.service_registrations == [trigger]
    assert kernel.context.children == []
    kernel.dispose()


@pytest.mark.parametrize("mode", ["emit", "parallel", "serial", "bail", "waterfall"])
def test_unregistration_preserves_inflight_dispatch_snapshot(mode):
    kernel = PluginKernel()
    trace = []
    holders = []

    def first(payload):
        trace.append("first")
        holders[0].dispose()

    def second(payload):
        trace.append("second")

    def first_waterfall(payload, next_):
        first(payload)
        return next_()

    def second_waterfall(payload, next_):
        second(payload)
        return next_()

    listener = kernel.context.on("change", first_waterfall if mode == "waterfall" else first, mode)
    holders.append(kernel.context.on("change", second_waterfall if mode == "waterfall" else second, mode))
    if mode == "waterfall":
        kernel.context.waterfall("change", None, lambda payload: trace.append("terminal"))
        assert trace == ["first", "second", "terminal"]
    else:
        getattr(kernel.context, mode)("change", None)
        assert trace == ["first", "second"]
    assert holders[0].callback is None
    assert kernel.context.event_registrations == [listener]
    listener.dispose()
    assert kernel.context.effects == kernel.context.event_registrations == []

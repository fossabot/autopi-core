import logging

from common_util import dict_get, dict_find, dict_filter
from messaging import EventDrivenMessageProcessor


log = logging.getLogger(__name__)

context = {
    "cache.get": lambda *args, **kwargs: dict_get(context.get("cache", None), *args, **kwargs),
    "cache.find": lambda *args, **kwargs: dict_find(context.get("cache", {}).values(), *args, **kwargs)
}

# Message processor
edmp = EventDrivenMessageProcessor("reactor", context=context)


@edmp.register_hook()
def module_handler(name, *args, **kwargs):
    """
    Calls a Salt execution module from within minion process.
    """

    return __salt__["minionutil.run_job"](name, *args, **kwargs)


@edmp.register_hook()
def module_direct_handler(name, *args, **kwargs):
    """
    Calls a Salt execution module directy from this engine process.
    """

    return __salt__[name](*args, **kwargs)


@edmp.register_hook()
def context_handler(key=None, **kwargs):
    """
    Queries or manipulatea context instance of this engine.
    """

    # Validate input
    if key != None and not kwargs:
        raise ValueError("No context data specified to set")
    elif key == None and kwargs:
        raise ValueError("A key must be specified to identify context data")

    ret = {}

    if key != None:
        ctx = context.setdefault(key, {})

        # Set new values if given
        for k, v in kwargs.iteritems():
            ctx[k.replace("__", ".")] = v

        ret["value"] = ctx
    else:
        ret["values"] = {k: v for k, v in context.iteritems() if not "." in k}

    return ret


@edmp.register_hook()
def echo_handler(event):
    """
    Mainly for testing.
    """

    log.info("Echo: {:}".format(event))


@edmp.register_hook()
def cache_handler(key=None, **kwargs):
    """
    Manages cached data.
    """

    # Validate input
    if key == None and kwargs:
        raise ValueError("A key must be given to identify cache data")

    ret = {}

    ctx = context.setdefault("cache", {})

    # List all cached items if not key is specified
    if key == None:
        ret["values"] = ctx

        return ret

    # Return cached entry for key if not data is specified
    if not kwargs:
        ret["value"] = ctx.get(key, {})

        return ret

    # Go ahead and update cache
    if not key in ctx or \
        dict_filter(ctx[key], lambda k: not k.startswith("_")) != dict_filter(kwargs, lambda k: not k.startswith("_")):
        kwargs["_count"] = 1
        ctx[key] = kwargs

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Inserted into cache '{:}: {:}".format(key, kwargs))

        ret["value"] = kwargs

    else:
        kwargs["_count"] = ctx[key]["_count"] + 1
        ctx[key] = kwargs

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Updated cache '{:}': {:}".format(key, kwargs))

        ret["value"] = kwargs

    return ret


@edmp.register_hook(synchronize=False)
def alternating_cache_event_filter(result):
    """
    Filter that only returns alternating/changed events from cache.
    """

    if result["value"]["_count"] != 1:
        return

    return result["value"]["event"]


def start(**settings):
    try:
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Starting event reactor with settings: {:}".format(settings))

        # Initialize and run message processor
        edmp.init(__salt__, __opts__,
            hooks=settings.get("hooks", []),
            workers=settings.get("workers", []),
            reactors=settings.get("reactors", []))
        edmp.run()

    except Exception:
        log.exception("Failed to start event reactor")

        raise
    finally:
        log.info("Stopping event reactor")

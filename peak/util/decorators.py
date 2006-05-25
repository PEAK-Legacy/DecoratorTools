from types import ClassType, FunctionType
import sys
__all__ = [
    'decorate_class', 'metaclass_is_decorator', 'metaclass_for_bases',
    'frameinfo', 'decorate_assignment', 'decorate',
]


def decorate(*decorators):
    """Use Python 2.4 decorators w/Python 2.3+

    Example::

        class Foo(object):
            decorate(classmethod)
            def something(cls,etc):
                \"""This is a classmethod\"""

    You can pass in more than one decorator, and they are applied in the same
    order that would be used for ``@`` decorators in Python 2.4.

    This function can be used to write decorator-using code that will work with
    both Python 2.3 and 2.4 (and up).
    """

    if len(decorators)>1:
        decorators = list(decorators)
        decorators.reverse()

    def callback(frame,k,v,old_locals):
        for d in decorators:
            v = d(v)
        return v

    return decorate_assignment(callback)






def frameinfo(frame):
    """Return (kind, module, locals, globals) tuple for a frame

    'kind' is one of "exec", "module", "class", "function call", or "unknown".
    """
    f_locals = frame.f_locals
    f_globals = frame.f_globals

    sameNamespace = f_locals is f_globals
    hasModule = '__module__' in f_locals
    hasName = '__name__' in f_globals
    sameName = hasModule and hasName
    sameName = sameName and f_globals['__name__']==f_locals['__module__']
    module = hasName and sys.modules.get(f_globals['__name__']) or None
    namespaceIsModule = module and module.__dict__ is f_globals

    if not namespaceIsModule:
        # some kind of funky exec
        kind = "exec"
        if hasModule and not sameNamespace:
            kind="class"
    elif sameNamespace and not hasModule:
        kind = "module"
    elif sameName and not sameNamespace:
        kind = "class"
    elif not sameNamespace:
        kind = "function call"
    else:
        # How can you have f_locals is f_globals, and have '__module__' set?
        # This is probably module-level code, but with a '__module__' variable.
        kind = "unknown"

    return kind,module,f_locals,f_globals








def decorate_class(decorator, depth=2, frame=None):

    """Set up `decorator` to be passed the containing class upon creation

    This function is designed to be called by a decorator factory function
    executed in a class suite.  The factory function supplies a decorator that
    it wishes to have executed when the containing class is created.  The
    decorator will be given one argument: the newly created containing class.
    The return value of the decorator will be used in place of the class, so
    the decorator should return the input class if it does not wish to replace
    it.

    The optional `depth` argument to this function determines the number of
    frames between this function and the targeted class suite.  `depth`
    defaults to 2, since this skips the caller's frame.  Thus, if you call this
    function from a function that is called directly in the class suite, the
    default will be correct, otherwise you will need to determine the correct
    depth value yourself.  Alternately, you can pass in a `frame` argument to
    explicitly indicate what frame is doing the class definition.

    This function works by installing a special class factory function in
    place of the ``__metaclass__`` of the containing class.  Therefore, only
    decorators *after* the last ``__metaclass__`` assignment in the containing
    class will be executed.  Thus, any classes using class decorators should
    declare their ``__metaclass__`` (if any) *before* specifying any class
    decorators, to ensure that all class decorators will be applied."""

    frame = frame or sys._getframe(depth)
    kind, module, caller_locals, caller_globals = frameinfo(frame)

    if kind != "class":
        raise SyntaxError(
            "Class decorators may only be used inside a class statement"
        )

    previousMetaclass = caller_locals.get('__metaclass__')
    defaultMetaclass  = caller_globals.get('__metaclass__', ClassType)




    def advise(name,bases,cdict):

        if '__metaclass__' in cdict:
            del cdict['__metaclass__']

        if previousMetaclass is None:
             if bases:
                 # find best metaclass or use global __metaclass__ if no bases
                 meta = metaclass_for_bases(bases)
             else:
                 meta = defaultMetaclass

        elif metaclass_is_decorator(previousMetaclass):
            # special case: we can't compute the "true" metaclass here,
            # so we need to invoke the previous metaclass and let it
            # figure it out for us (and apply its own advice in the process)
            meta = previousMetaclass

        else:
            meta = metaclass_for_bases(bases, previousMetaclass)

        newClass = meta(name,bases,cdict)

        # this lets the decorator replace the class completely, if it wants to
        return decorator(newClass)

    # introspection data only, not used by inner function
    # Note: these attributes cannot be renamed or it will break compatibility
    # with zope.interface and any other code that uses this decoration protocol
    advise.previousMetaclass = previousMetaclass
    advise.callback = decorator

    # install the advisor
    caller_locals['__metaclass__'] = advise


def metaclass_is_decorator(ob):
    """True if 'ob' is a class advisor function"""
    return isinstance(ob,FunctionType) and hasattr(ob,'previousMetaclass')


def metaclass_for_bases(bases, explicit_mc=None):
    """Determine metaclass from 1+ bases and optional explicit __metaclass__"""

    meta = [getattr(b,'__class__',type(b)) for b in bases]

    if explicit_mc is not None:
        # The explicit metaclass needs to be verified for compatibility
        # as well, and allowed to resolve the incompatible bases, if any
        meta.append(explicit_mc)

    if len(meta)==1:
        # easy case
        return meta[0]

    classes = [c for c in meta if c is not ClassType]
    candidates = []

    for m in classes:
        for n in classes:
            if issubclass(n,m) and m is not n:
                break
        else:
            # m has no subclasses in 'classes'
            if m in candidates:
                candidates.remove(m)    # ensure that we're later in the list
            candidates.append(m)

    if not candidates:
        # they're all "classic" classes
        return ClassType

    elif len(candidates)>1:
        # We could auto-combine, but for now we won't...
        raise TypeError("Incompatible metatypes",bases)

    # Just one, return it
    return candidates[0]




def decorate_assignment(callback, depth=2, frame=None):
    """Invoke 'callback(frame,name,value,old_locals)' on next assign in 'frame'

    The frame monitored is determined by the 'depth' argument, which gets
    passed to 'sys._getframe()'.  When 'callback' is invoked, 'old_locals'
    contains a copy of the frame's local variables as they were before the
    assignment took place, allowing the callback to access the previous value
    of the assigned variable, if any.  The callback's return value will become
    the new value of the variable.  'name' is the name of the variable being
    created or modified, and 'value' is its value (the same as
    'frame.f_locals[name]').

    This function also returns a decorator function for forward-compatibility
    with Python 2.4 '@' syntax.  Note, however, that if the returned decorator
    is used with Python 2.4 '@' syntax, the callback 'name' argument may be
    'None' or incorrect, if the 'value' is not the original function (e.g.
    when multiple decorators are used).
    """
    frame = frame or sys._getframe(depth)
    oldtrace = [frame.f_trace]
    old_locals = frame.f_locals.copy()

    def tracer(frm,event,arg):
        if event=='call':
            # We don't want to trace into any calls
            if oldtrace[0]:
                # ...but give the previous tracer a chance to, if it wants
                return oldtrace[0](frm,event,arg)
            else:
                return None

        try:
            if frm is frame and event !='exception':
                # Aha, time to check for an assignment...
                for k,v in frm.f_locals.items():
                    if k not in old_locals or old_locals[k] is not v:
                        break
                else:
                    # No luck, keep tracing
                    return tracer

                # Got it, fire the callback, then get the heck outta here...
                frm.f_locals[k] = callback(frm,k,v,old_locals)

        finally:
            # Give the previous tracer a chance to run before we return
            if oldtrace[0]:
                # And allow it to replace our idea of the "previous" tracer
                oldtrace[0] = oldtrace[0](frm,event,arg)

        uninstall()
        return oldtrace[0]

    def uninstall():
        # Unlink ourselves from the trace chain.
        frame.f_trace = oldtrace[0]
        sys.settrace(oldtrace[0])

    # Install the trace function
    frame.f_trace = tracer
    sys.settrace(tracer)

    def do_decorate(f):
        # Python 2.4 '@' compatibility; call the callback
        uninstall()
        frame = sys._getframe(1)
        return callback(
            frame, getattr(f,'__name__',None), f, frame.f_locals
        )

    return do_decorate












Class, Function, and Assignment Decorators for Python 2.3+
==========================================================

(NEW in 1.1: The ``struct()`` decorator makes it easy to create tuple-like data
structure types, by decorating a constructor function.)

Want to use decorators, but still need to support Python 2.3?  Wish you could
have class decorators, or decorate arbitrary assignments?  Then you need
"DecoratorTools".  Some quick examples::

    # Method decorator example
    from peak.util.decorators import decorate

    class Demo1(object):
        decorate(classmethod)   # equivalent to @classmethod
        def example(cls):
            print "hello from", cls


    # Class decorator example
    from peak.util.decorators import decorate_class

    def my_class_decorator():
        def decorator(cls):
            print "decorating", cls
            return cls
        decorate_class(decorator)

    class Demo2:
        my_class_decorator()

    # "decorating <class Demo2>" will be printed when execution gets here


Installing DecoratorTools (using ``"easy_install DecoratorTools"`` or
``"setup.py install"``) gives you access to the ``peak.util.decorators``
module.  The tools in this module have been bundled for years inside of PEAK,
PyProtocols, RuleDispatch, and the zope.interface package, so they have been
widely used and tested.  (Unit tests are also included, of course.)

This standalone version is backward-compatible with the bundled versions, so you
can mix and match decorators from this package with those provided by
zope.interface, TurboGears, etc.


.. contents:: **Table of Contents**

You may access any of the following APIs by importing them from
``peak.util.decorators``:


Simple Decorators
-----------------

decorate(\*decorators)
    Apply `decorators` to the subsequent function definition or assignment
    statement, thereby allowing you to conviently use standard decorators with
    Python 2.3 and up (i.e., no ``@`` syntax required), as shown in the
    following table of examples::

        Python 2.4+               DecoratorTools
        ------------              --------------
        @classmethod              decorate(classmethod)
        def blah(cls):            def blah(cls):
            pass                      pass

        @foo
        @bar(baz)                 decorate(foo, bar(baz))
        def spam(bing):           def spam(bing):
            """whee"""                """whee"""

decorate_class(decorator [, depth=2, frame=None])
    Set up `decorator` to be passed the containing class after its creation.

    This function is designed to be called by a decorator factory function
    executed in a class suite.  It is not used directly; instead you simply
    give your users a "magic function" to call in the body of the appropriate
    class.  Your "magic function" (i.e. a decorator factory function) then
    calls ``decorate_class`` to register the decorator to be called when the
    class is created.  Multiple decorators may be used within a single class,
    although they must all appear *after* the ``__metaclass__`` declaration, if
    there is one.

    The registered decorator will be given one argument: the newly created
    containing class.  The return value of the decorator will be used in place
    of the original class, so the decorator should return the input class if it
    does not wish to replace it.  Example::

        from peak.util.decorators import decorate_class

        def demo_class_decorator():
            def decorator(cls):
                print "decorating", cls
                return cls
            decorate_class(decorator)

        class Demo:
            demo_class_decorator()  # this will print "decorating <class Demo>"

    In the above example, ``demo_class_decorator()`` is the decorator factory
    function, and its inner function ``decorator`` is what gets called to
    actually decorate the class.  Notice that the factory function has to be
    called within the class body, even if it doesn't take any arguments.

    If you are just creating simple class decorators, you don't need to worry
    about the `depth` or `frame` arguments here.  However, if you are creating
    routines that are intended to be used within other class or method
    decorators, you will need to pay attention to these arguments to ensure
    that ``decorate_class()`` can find the frame where the class is being
    defined.  In general, the simplest way to do this is for the function
    that's called in the class body to get its caller's frame with
    ``sys._getframe(1)``, and then pass that frame down to whatever code will
    be calling ``decorate_class()``.  Alternately, you can specify the `depth`
    that ``decorate_class()`` should call ``sys._getframe()`` with, but this
    can be a bit trickier to compute correctly.


The ``struct()`` Decorator
--------------------------

The ``struct()`` decorator creates a tuple subclass with the same name and
docstring as the decorated function.  The class will have read-only properties
with the same names as the function's arguments, and the ``repr()`` of its
instances will look like a call to the original function::

    >>> from peak.util.decorators import struct

    >>> def X(a,b,c):
    ...     """Demo type"""
    ...     return a,b,c

    >>> X = struct()(X)    # can't use decorators above functions in doctests

    >>> v = X(1,2,3)
    >>> v
    X(1, 2, 3)
    >>> v.a
    1
    >>> v.b
    2
    >>> v.c
    3

    >>> help(X)
    Help on class X:
    <BLANKLINE>
    class X(__builtin__.tuple)
     |  Demo type
     |
     |  Method resolution order:
     |      X
     |      __builtin__.tuple
     |      __builtin__.object
     |
     |  Methods defined here:
     |
     |  __repr__(self)
     |
     |  ----------------------------------------------------------------------
     |  Static methods defined here:
     |
     |  __new__(cls, *args, **kw)
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors defined here:
     |
     |  a
     |
     |  b
     |
     |  c
     |
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |
     |  __args__ = ['a', 'b', 'c']
     |
     |  __star__ = None
     |
     |  ...

The function should return a tuple of values in the same order as its argument
names, as it will be used by the class' constructor. The function can perform
validation, add defaults, and/or do type conversions on the values.

If the function takes a ``*``, argument, it should flatten this argument
into the result tuple, e.g.::

    >>> def pair(first, *rest):
    ...     return (first,) + rest
    >>> pair = struct()(pair)

    >>> p = pair(1,2,3,4)
    >>> p
    pair(1, 2, 3, 4)
    >>> p.first
    1
    >>> p.rest
    (2, 3, 4)

The ``struct()`` decorator takes optional mixin classes (as positional
arguments), and dictionary entries (as keyword arguments).  The mixin
classes will be placed before ``tuple`` in the resulting class' bases, and
the dictionary entries will be placed in the class' dictionary.  These
entries take precedence over any default entries (e.g. methods, properties,
docstring, etc.) that are created by the ``struct()`` decorator::

    >>> class Mixin(object):
    ...     __slots__ = []
    ...     def foo(self): print "bar"

    >>> def demo(a, b):
    ...     return a, b

    >>> demo = struct(Mixin, reversed=property(lambda self: self[::-1]))(demo)
    >>> demo(1,2).foo()
    bar
    >>> demo(3,4).reversed
    (4, 3)
    >>> demo.__mro__
    (<class 'demo'>, <class ...Mixin...>, <type 'tuple'>, <type 'object'>)

Note that using mixin classes will result in your new class' instances having
a ``__dict__`` attribute, unless they are new-style classes that set
``__slots__`` to an empty list.  And if they have any slots other than
``__weakref__`` or ``__dict__``, this will cause a type error due to layout
conflicts.  In general, it's best to use mixins only for adding methods, not
data.

Finally, note that if your function returns a non-tuple result, it will be
returned from the class' constructor.  This is sometimes useful::

    >>> def And(a, b):
    ...     if a is None: return b
    ...     return a, b
    >>> And = struct()(And)

    >>> And(1,2)
    And(1, 2)

    >>> And(None, 27)
    27


Advanced Decorators
-------------------

The ``decorate_assignment()`` function can be used to create standalone "magic"
decorators that work in Python 2.3 and up, and which can also be used to
decorate arbitrary assignments as well as function/method definitions.  For
example, if you wanted to create an ``info(**kwargs)`` decorator that could be
used either with or without an ``@``, you could do something like::

    from peak.util.decorators import decorate_assignment

    def info(**kw):
        def callback(frame, name, func, old_locals):
            func.__dict__.update(kw)
            return func
        return decorate_assignment(callback)

    info(foo="bar")     # will set dummy.foo="bar"; @info() would also work
    def dummy(blah):
        pass

As you can see, this ``info()`` decorator can be used without an ``@`` sign
for backward compatibility with Python 2.3.  It can also be used *with* an
``@`` sign, for forward compatibility with Python 2.4 and up.

Here's a more detailed reference for the ``decorate_assignment()`` API:

decorate_assignment(callback [, depth=2, frame=None])
    Call `callback(frame, name, value, old_locals)` on next assign in `frame`.

    If a `frame` isn't supplied, a frame is obtained using
    ``sys._getframe(depth)``.  `depth` defaults to 2 so that the correct frame
    is found when ``decorate_assignment()`` is called from a decorator factory
    that was called in the target usage context.

    When `callback` is invoked, `old_locals` contains the frame's local
    variables as they were *before* the assignment, thus allowing the callback
    to access the previous value of the assigned variable, if any.

    The callback's return value will become the new value of the variable.
    `name` will contain the name of the variable being created or modified,
    and `value` will be the thing being decorated.  `frame` is the Python frame
    in which the assignment occurred.

    This function also returns a decorator function for forward-compatibility
    with Python 2.4 ``@`` syntax.  Note, however, that if the returned decorator
    is used with Python 2.4 ``@`` syntax, the callback `name` argument may be
    ``None`` or incorrect, if the `value` is not the original function (e.g.
    when multiple decorators are used).


Utility/Introspection Functions
-------------------------------

``peak.util.decorators`` also exposes these additional utility and
introspection functions that it uses internally:

frameinfo(frame)
    Return a ``(kind, module, locals, globals)`` tuple for a frame

    The `kind` returned is a string, with one of the following values:

    * ``"exec"``
    * ``"module"``
    * ``"class"``
    * ``"function call"``
    * ``"unknown"``

    The `module` returned is the Python module object whose globals are in
    effect for the frame, or ``None`` if the globals don't include a value for
    ``__name__``.

metaclass_is_decorator(mc)
    Return truth if the given metaclass is a class decorator metaclass inserted
    into a class by ``decorate_class()``, or by another class decorator
    implementation that follows the same protocol (such as the one in
    ``zope.interface``).

metaclass_for_bases(bases, explicit_mc=None)
    Given a sequence of 1 or more base classes and an optional explicit
    ``__metaclass__``, return the metaclass that should be used.  This
    routine basically emulates what Python does to determine the metaclass
    when creating a class, except that it does *not* take a module-level
    ``__metaclass__`` into account, only the arguments as given.  If there
    are no base classes, you should just directly use the module-level
    ``__metaclass__`` or ``types.ClassType`` if there is none.


Mailing List
------------

Please direct questions regarding this package to the PEAK mailing list; see
http://www.eby-sarna.com/mailman/listinfo/PEAK/ for details.

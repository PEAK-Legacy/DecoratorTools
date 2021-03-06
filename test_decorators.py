from unittest import TestCase, makeSuite, TestSuite
from peak.util.decorators import *
from peak.util.decorators import with_metaclass
import sys

def ping(log, value):

    """Class decorator for testing"""

    def pong(klass):
        log.append((value,klass))
        return [klass]

    decorate_class(pong)


def additional_tests():
    import doctest
    return doctest.DocFileSuite(
        'README.txt',
        optionflags=doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE,
    )



















class DecoratorTests(TestCase):

    def testAssignAdvice(self):

        log = []
        def track(f,k,v,d):
            log.append((f,k,v))
            if k in f.f_locals:
                del f.f_locals[k]   # simulate old-style advisor

        decorate_assignment(track,frame=sys._getframe())
        test_var = 1
        self.assertEqual(log, [(sys._getframe(),'test_var',1)])
        log = []
        decorate_assignment(track,1)
        test2 = 42
        self.assertEqual(log, [(sys._getframe(),'test2',42)])

        # Try doing double duty, redefining an existing variable...
        log = []
        decorate_assignment(track,1)
        decorate_assignment(track,1)

        test2 = 42
        self.assertEqual(log, [(sys._getframe(),'test2',42)]*2)


    def testAs(self):

        def f(): pass

        [decorate(lambda x: [x])]
        f1 = f

        self.assertEqual(f1, [f])

        [decorate(list, lambda x: (x,))]
        f1 = f
        self.assertEqual(f1, [f])


    def test24DecoratorMode(self):
        log = []
        def track(f,k,v,d):
            log.append((f,k,v))
            return v

        def foo(x): pass

        decorate_assignment(track,1)(foo)
        x = 1

        self.assertEqual(log, [(sys._getframe(),'foo',foo)])

    def testAlreadyTracing(self):
        log = []; stk = []
        fue = self.assertEqual.__name__ #['failUnlessEqual']
        def my_global_tracer(frm,event,arg):
            if not stk: log.append(frm.f_code.co_name)
            if frm.f_code.co_name==fue:
                stk.append(frm)
            return my_local_tracer
        def my_local_tracer(frm, event, arg):
            if event=='return' and stk and stk[-1] is frm:
                stk.pop()
            return my_local_tracer

        sys.settrace(my_global_tracer)  # This is going to break your debugger!
        self.testAssignAdvice()
        sys.settrace(None)
        # And this part is going to fail if testAssignAdvice() or
        # decorate_assignment change much...
        self.assertEqual(log, [
            'testAssignAdvice',
            'decorate_assignment', 'enclosing_frame', '<lambda>', fue,
            'decorate_assignment', 'enclosing_frame', '<lambda>', fue,
            'decorate_assignment', 'enclosing_frame', '<lambda>',
            'decorate_assignment', 'enclosing_frame', '<lambda>', fue,
        ])
            


moduleLevelFrameInfo = frameinfo(sys._getframe())

class FrameInfoTest(TestCase):

    classLevelFrameInfo = frameinfo(sys._getframe())

    def testModuleInfo(self):
        kind,module,f_locals,f_globals = moduleLevelFrameInfo
        assert kind=="module"
        for d in module.__dict__, f_locals, f_globals:
            assert d is globals()

    def testClassInfo(self):
        kind,module,f_locals,f_globals = self.classLevelFrameInfo
        assert kind=="class"
        assert f_locals['classLevelFrameInfo'] is self.classLevelFrameInfo
        for d in module.__dict__, f_globals:
            assert d is globals()


    def testCallInfo(self):
        kind,module,f_locals,f_globals = frameinfo(sys._getframe())
        assert kind=="function call"
        assert f_locals is locals() # ???
        for d in module.__dict__, f_globals:
            assert d is globals()


    def testClassExec(self):
        d = {'sys':sys, 'frameinfo':frameinfo}
        exec("class Foo: info=frameinfo(sys._getframe())", d)
        kind,module,f_locals,f_globals = d['Foo'].info
        assert kind=="class", kind








class ClassDecoratorTests(TestCase):

    def testOrder(self):
        log = []
        class Foo:
            ping(log, 1)
            ping(log, 2)
            ping(log, 3)

        # Strip the list nesting
        for i in 1,2,3:
            assert isinstance(Foo,list)
            Foo, = Foo

        assert log == [
            (1, Foo),
            (2, [Foo]),
            (3, [[Foo]]),
        ]

    def testOutside(self):
        try:
            ping([], 1)
        except SyntaxError:
            pass
        else:
            raise AssertionError(
                "Should have detected advice outside class body"
            )

    def testDoubleType(self):
        if sys.hexversion >= 0x02030000:
            return  # you can't duplicate bases in 2.3
        class aType(type,type):
            ping([],1)
        aType, = aType
        assert aType.__class__ is type




    def testSingleExplicitMeta(self):

        class M(type): pass

        class C(with_metaclass(M, M)):
            ping([],1)

        C, = C
        assert C.__class__ is M


    def testMixedMetas(self):

        class M1(type): pass
        class M2(type): pass

        class B1(with_metaclass(M1)): pass
        class B2(with_metaclass(M2)): pass

        try:
            class C(B1,B2):
                ping([],1)
        except TypeError:
            pass
        else:
            raise AssertionError("Should have gotten incompatibility error")

        class M3(M1,M2): pass

        class C(with_metaclass(M3,B1,B2)):
            ping([],1)

        assert isinstance(C,list)
        C, = C
        assert isinstance(C,M3)






    def testMetaOfClass(self):

        class metameta(type):
            pass

        class meta(with_metaclass(metameta, type)):
            pass

        assert metaclass_for_bases((meta,type))==metameta


class ClassyMetaTests(TestCase):
    """Test subclass/instance checking of classy for Python 2.6+ ABC mixin"""

    # avert 3.2 warnings, but still work on 2.3(!)
    failUnless = getattr(TestCase, 'assertTrue', TestCase.failUnless)
    failIf = getattr(TestCase, 'assertFalse', TestCase.failIf)

    def setUp(self):
        class x(classy): pass
        class y(x): pass
        class cc(type(classy)): pass
        self.__dict__.update(locals())

    def test_subclassing(self):
        self.failUnless(issubclass(self.x, classy))
        self.failUnless(issubclass(self.y, self.x))
        self.failIf(issubclass(self.x, self.y))
        self.failIf(issubclass(classy, self.x))
        self.failIf(issubclass(self.x, type(classy)))

    def test_instancing(self):
        self.failIf(isinstance(self.x, classy))
        self.failUnless(isinstance(self.x, type(classy)))
        self.failIf(isinstance(self.x(), type(classy)))
        self.failIf(isinstance(object, type(classy)))
        self.failIf(isinstance(self.x(),self.y))
        self.failUnless(isinstance(self.y(),self.x))




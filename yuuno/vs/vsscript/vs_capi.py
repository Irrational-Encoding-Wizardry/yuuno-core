from yuuno.vs.vsscript.capsules import Capsules
import vapoursynth
import functools

import ctypes


class Counter(object):
    def __init__(self):
        self._counter = 0

    def __call__(self):
        self._counter += 1
        return self._counter


_run_counter = Counter()
_script_counter = Counter()


class VPYScriptExport(ctypes.Structure):
    _fields_ = [
        ('pyenvdict', ctypes.py_object),
        ('errstr', ctypes.c_void_p),
        ('id', ctypes.c_int)
    ]


class _VapourSynthCAPI(Capsules):
    _module_ = vapoursynth

    vpy_initVSScript   = ctypes.CFUNCTYPE(ctypes.c_int)
    vpy_createScript   = ctypes.CFUNCTYPE(ctypes.c_int,    ctypes.POINTER(VPYScriptExport))
    vpy_getError       = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.POINTER(VPYScriptExport))
    vpy_evaluateScript = ctypes.CFUNCTYPE(ctypes.c_int,    ctypes.POINTER(VPYScriptExport), ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int)
    vpy_getVSApi       = ctypes.CFUNCTYPE(ctypes.c_void_p)
    vpy_freeScript     = ctypes.CFUNCTYPE(None,            ctypes.POINTER(VPYScriptExport))


VapourSynthCAPI = _VapourSynthCAPI()


def enable_vsscript():
    if VapourSynthCAPI.vpy_getVSApi() == ctypes.c_void_p(0):
        raise OSError("Couldn't detect a VapourSynth API Instance")
    if VapourSynthCAPI.vpy_initVSScript():
        raise OSError("Failed to initialize VSScript.")
    if not vapoursynth._using_vsscript:
        raise RuntimeError("Failed to enable vsscript.")


def disable_vsscript():
    if not vapoursynth._using_vsscript:
        return
    vapoursynth._using_vsscript = False


def _perform_in_environment(func):
    @functools.wraps(func)
    def _wrapper(self, *args, **kwargs):
        return self.perform(lambda: func(self, *args, **kwargs))
    return _wrapper


class ScriptEnvironment(object):
    def __init__(self, filename=None):
        enable_vsscript()
        self.filename = filename
        self.id = _script_counter()
        self.export = VPYScriptExport()
        self.export.pyenvdict = {}
        self.export.id = self.id
        if VapourSynthCAPI.vpy_createScript(self._handle):
            self._raise_error()

        self._core = None
        self._outputs = None

    @property
    def _handle(self):
        if self.export is None:
            return
        return ctypes.pointer(self.export)

    @property
    def alive(self):
        return self.export is not None

    def dispose(self):
        if self.export is None:
            return
        VapourSynthCAPI.vpy_freeScript(self._handle)
        self.export = None

    def _raise_error(self):
        raise vapoursynth.Error(VapourSynthCAPI.vpy_getError(self._handle).decode('utf-8'))

    def perform(self, func, counter=None):
        if self.export is None:
            raise vapoursynth.Error("Tried to access dead core.")

        if not counter:
            counter = _run_counter()
        name = '__yuuno_%d_run_%d' % (id(self), counter)

        result = None
        error = None

        def _execute_func():
            nonlocal result, error

            try:
                result = func()
            except Exception as e:
                error = e

        filename = '<Yuuno:%d>' % counter
        if self.filename:
            filename = self.filename
        filename = filename.encode('utf-8')

        self.export.pyenvdict[name] = _execute_func
        try:
            if VapourSynthCAPI.vpy_evaluateScript(self._handle, ('%s()' % name).encode('ascii'), filename, 0):
                self._raise_error()
        finally:
            del self.export.pyenvdict[name]

        if error is not None:
            raise error
        return result

    def exec(self, code):
        counter = _run_counter()
        compiled = compile(code, '<Yuuno %r:%d>' % (self.filename, counter), 'exec')

        def _exec():
            exec(compiled, self.export.pyenvdict, {})

        self.perform(_exec, counter)

    @_perform_in_environment
    def _get_core(self):
        return vapoursynth.get_core()

    @property
    def core(self):
        if self._core is None:
            self._core = self._get_core()
        return self._core

    @_perform_in_environment
    def _get_outputs(self):
        return vapoursynth.get_outputs()

    @property
    def outputs(self):
        if self._outputs is None:
            self._outputs = self._get_outputs()
        return self._outputs

    def get_output(self, index=0):
        return self.outputs[index]

    def __del__(self):
        self.dispose()

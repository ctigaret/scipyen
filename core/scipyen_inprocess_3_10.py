from ipykernel.inprocess.ipkernel import InProcessKernel
class ScipyenInProcessKernel(InProcessKernel):
    """Workaround the following exception when using InProcessKernel (see below).
    
    Traceback (most recent call last):
    File "/home/.../scipyenv39/lib64/python3.9/site-packages/tornado/ioloop.py", line 741, in _run_callback
        ret = callback()
    File "/home/.../scipyenv39/lib/python3.9/site-packages/ipykernel/kernelbase.py", line 419, in enter_eventloop
        schedule_next()
    File "/home/.../scipyenv39/lib/python3.9/site-packages/ipykernel/kernelbase.py", line 416, in schedule_next
        self.io_loop.call_later(0.001, advance_eventloop)
    AttributeError: 'InProcessKernel' object has no attribute 'io_loop'
    
    See also https://github.com/ipython/ipykernel/issues/319
    
    (NOTE: This DOES NOT crash the kernel):
    ERROR:tornado.application:Exception in callback 
    functools.partial(<bound method Kernel.enter_eventloop of <ipykernel.inprocess.ipkernel.InProcessKernel object at 0x7f0b6abe5730>>)
    
    It turns out that all we need is to set eventloop to None so that tornado
    "stays put".
    
    NOTE: 2022-03-05 16:36:35
    In addition, ScipyenInProcessKernel also overrides execute_request to await 
    for the _abort_queues instead of calling them directly, see below, at
    NOTE: 2022-03-05 16:04:03
    
    (It is funny that this happens in Scipyen, because this warning does not
    appear in jupyter qtconsole launched in the same virtual Python environment
    as Scipyen (Python 3.10.2), and I don't think this has anything to do with 
    setting eventloop to None)

    """
    eventloop = None
    
    def __init__(self, **traits):
        super().__init__(**traits)
        
    @asyncio.coroutine
    def _abort_queues(self):
        yield
    
    async def execute_request(self, stream, ident, parent):
        """handle an execute_request
        
        Overrides ipykernel.inprocess.ipkernel.InProcessKernel which in turn
        calls ipykernel.kernelbase.Kernel.execute_request, to fix the issue below
        
        NOTE: 2022-03-05 16:04:03
        
        In the InProcessKernel _abort_queues is a coroutine and not a method 
        (function); this raises the RuntimeWarning: 
        coroutine 'InProcessKernel._abort_queues' was never awaited.
        
        """

        with self._redirected_io(): # NOTE: 2022-03-14 22:12:02 this is ESSENTIAL!!!
            try:
                content = parent['content']
                code = content['code']
                silent = content['silent']
                store_history = content.get('store_history', not silent)
                user_expressions = content.get('user_expressions', {})
                allow_stdin = content.get('allow_stdin', False)
            except Exception:
                self.log.error("Got bad msg: ")
                self.log.error("%s", parent)
                return

            stop_on_error = content.get('stop_on_error', True)

            metadata = self.init_metadata(parent)

            # Re-broadcast our input for the benefit of listening clients, and
            # start computing output
            if not silent:
                self.execution_count += 1
                self._publish_execute_input(code, parent, self.execution_count)

            reply_content = self.do_execute(
                code, silent, store_history,
                user_expressions, allow_stdin,
            )
            if inspect.isawaitable(reply_content):
                reply_content = await reply_content

            # Flush output before sending the reply.
            sys.stdout.flush()
            sys.stderr.flush()
            # FIXME: on rare occasions, the flush doesn't seem to make it to the
            # clients... This seems to mitigate the problem, but we definitely need
            # to better understand what's going on.
            if self._execute_sleep:
                time.sleep(self._execute_sleep)

            # Send the reply.
            reply_content = json_clean(reply_content)
            metadata = self.finish_metadata(parent, metadata, reply_content)

            reply_msg = self.session.send(stream, 'execute_reply',
                                        reply_content, parent, metadata=metadata,
                                        ident=ident)

            self.log.debug("%s", reply_msg)

            if not silent and reply_msg['content']['status'] == 'error' and stop_on_error:
                # NOTE: 2022-03-05 16:04:10 
                # this apparently fixes the issue at NOTE: 2022-03-05 16:04:03
                await self._abort_queues() 


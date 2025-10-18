Here’s what that log is telling us:

- ✅ The first few manifestos (CDU, SPD, AfD, Linke, FDP) actually converted and chunked successfully. You can see each `Finished converting …` and later `Finished parsing …` / `Finished chunking …` message for them.

- ❌ During the next batch (right after those successes) the background task that writes chunks back to Postgres tried to refresh an ORM view and needed a new database connection. Every slot in the SQLAlchemy pool was already in use—and at least one was still marked `INTRANS` (open transaction) because earlier document-processing tasks hadn’t returned their connections yet. When SQLAlchemy tried to open another connection it hit the Postgres pool timeout (`psycopg.errors.ConnectionTimeout`). That’s the long stack trace you pasted.

  - In short: chunking is working, but the background jobs are holding DB sessions open too long. Once several large PDFs are being processed concurrently, the pool runs dry and the next job times out while waiting for a free connection.

  - The fix is to ensure every document-processing branch either commits/rolls back and explicitly closes its session (or relies on `async with sessionmaker()` so it auto-closes). Increasing the pool size helps temporarily but doesn’t solve the leak.

- ⚠️ A little later in the same run you also see `WeaviateInsertManyAllFailedError … OpenAI API failed … maximum context length 8192 tokens` for one batch. That’s separate: a chunk generated from one manifesto exceeded GPT-4 embeddings’ token limit. The client stops that entire batch, logs the error, then moves on. We need to clamp chunk size (or drop overly long paragraphs) before sending them to Weaviate so that the embeddings endpoint never sees >8192 tokens.

So the headline: chunking itself succeeded for most PDFs, but (1) the background chunk-writer is leaking DB connections, leading to the `psycopg.errors.ConnectionTimeout`, and (2) at least one chunk batch exceeds the OpenAI token limit, so Weaviate rejects it. Fix both and the pipeline should run cleanly for the remaining manifestos.




### My roginal Prompt including errorlog:
okay now lets go back to evaluating the chunking. i think iit orked for most party docuemtn manifesto pdfs. but not all in want you to look at the backend log and tell me why this happened: ~~~~~~~~~~~~~~~~~~~~~~^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 1264, in _checkout
electomate-backend  |     fairy = _ConnectionRecord.checkout(pool)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 716, in checkout
electomate-backend  |     with util.safe_reraise():
electomate-backend  |          ~~~~~~~~~~~~~~~~~^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
electomate-backend  |     raise exc_value.with_traceback(exc_tb)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 714, in checkout
electomate-backend  |     dbapi_connection = rec.get_connection()
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 836, in get_connection
electomate-backend  |     self.__connect()
electomate-backend  |     ~~~~~~~~~~~~~~^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 899, in __connect
electomate-backend  |     with util.safe_reraise():
electomate-backend  |          ~~~~~~~~~~~~~~~~~^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
electomate-backend  |     raise exc_value.with_traceback(exc_tb)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 895, in __connect
electomate-backend  |     self.dbapi_connection = connection = pool._invoke_creator(self)
electomate-backend  |                                          ~~~~~~~~~~~~~~~~~~~~^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/create.py", line 661, in connect
electomate-backend  |     return dialect.connect(*cargs, **cparams)
electomate-backend  |            ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/default.py", line 629, in connect
electomate-backend  |     return self.loaded_dbapi.connect(*cargs, **cparams)  # type: ignore[no-any-return]  # NOQA: E501
electomate-backend  |            ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/psycopg.py", line 733, in connect
electomate-backend  |     await_only(creator_fn(*arg, **kw))
electomate-backend  |     ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
electomate-backend  |     return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
electomate-backend  |            ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
electomate-backend  |     value = await result
electomate-backend  |             ^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/psycopg/connection_async.py", line 140, in connect
electomate-backend  |     raise last_ex.with_traceback(None)
electomate-backend  | psycopg.errors.ConnectionTimeout: connection timeout expired
electomate-backend  | 
electomate-backend  | The above exception was the direct cause of the following exception:
electomate-backend  | 
electomate-backend  | Traceback (most recent call last):
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
electomate-backend  |     result = await app(  # type: ignore[func-returns-value]
electomate-backend  |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |         self.scope, self.receive, self.send
electomate-backend  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |     )
electomate-backend  |     ^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
electomate-backend  |     return await self.app(scope, receive, send)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/applications.py", line 1133, in __call__
electomate-backend  |     await super().__call__(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/applications.py", line 113, in __call__
electomate-backend  |     await self.middleware_stack(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 186, in __call__
electomate-backend  |     raise exc
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 164, in __call__
electomate-backend  |     await self.app(scope, receive, _send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette_context/middleware/raw_middleware.py", line 94, in __call__
electomate-backend  |     await self.app(scope, receive, send_wrapper)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 189, in __call__
electomate-backend  |     raise app_exc
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 144, in coro
electomate-backend  |     await self.app(scope, receive_or_disconnect, send_no_error)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py", line 85, in __call__
electomate-backend  |     await self.app(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
electomate-backend  |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
electomate-backend  |     raise exc
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
electomate-backend  |     await app(scope, receive, sender)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
electomate-backend  |     await self.app(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/routing.py", line 716, in __call__
electomate-backend  |     await self.middleware_stack(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/routing.py", line 736, in app
electomate-backend  |     await route.handle(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/routing.py", line 290, in handle
electomate-backend  |     await self.app(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 123, in app
electomate-backend  |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
electomate-backend  |     raise exc
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
electomate-backend  |     await app(scope, receive, sender)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 110, in app
electomate-backend  |     await response(scope, receive, send)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/responses.py", line 168, in __call__
electomate-backend  |     await self.background()
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/background.py", line 42, in __call__
electomate-backend  |     await task()
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/background.py", line 27, in __call__
electomate-backend  |     await self.func(*self.args, **self.kwargs)
electomate-backend  |   File "/app/src/em_backend/api/routers/documents.py", line 99, in process_document
electomate-backend  |     await session.refresh(document_view)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/ext/asyncio/session.py", line 331, in refresh
electomate-backend  |     await greenlet_spawn(
electomate-backend  |     ...<4 lines>...
electomate-backend  |     )
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
electomate-backend  |     result = context.throw(*sys.exc_info())
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/orm/session.py", line 3168, in refresh
electomate-backend  |     loading.load_on_ident(
electomate-backend  |     ~~~~~~~~~~~~~~~~~~~~~^
electomate-backend  |         self,
electomate-backend  |         ^^^^^
electomate-backend  |     ...<10 lines>...
electomate-backend  |         is_user_refresh=True,
electomate-backend  |         ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |     )
electomate-backend  |     ^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/orm/loading.py", line 510, in load_on_ident
electomate-backend  |     return load_on_pk_identity(
electomate-backend  |         session,
electomate-backend  |     ...<11 lines>...
electomate-backend  |         is_user_refresh=is_user_refresh,
electomate-backend  |     )
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/orm/loading.py", line 695, in load_on_pk_identity
electomate-backend  |     session.execute(
electomate-backend  |     ~~~~~~~~~~~~~~~^
electomate-backend  |         q,
electomate-backend  |         ^^
electomate-backend  |     ...<2 lines>...
electomate-backend  |         bind_arguments=bind_arguments,
electomate-backend  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |     )
electomate-backend  |     ^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/orm/session.py", line 2365, in execute
electomate-backend  |     return self._execute_internal(
electomate-backend  |            ~~~~~~~~~~~~~~~~~~~~~~^
electomate-backend  |         statement,
electomate-backend  |         ^^^^^^^^^^
electomate-backend  |     ...<4 lines>...
electomate-backend  |         _add_event=_add_event,
electomate-backend  |         ^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |     )
electomate-backend  |     ^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/orm/session.py", line 2241, in _execute_internal
electomate-backend  |     conn = self._connection_for_bind(bind)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/orm/session.py", line 2110, in _connection_for_bind
electomate-backend  |     return trans._connection_for_bind(engine, execution_options)
electomate-backend  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "<string>", line 2, in _connection_for_bind
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/orm/state_changes.py", line 137, in _go
electomate-backend  |     ret_value = fn(self, *arg, **kw)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/orm/session.py", line 1189, in _connection_for_bind
electomate-backend  |     conn = bind.connect()
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 3277, in connect
electomate-backend  |     return self._connection_cls(self)
electomate-backend  |            ~~~~~~~~~~~~~~~~~~~~^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 145, in __init__
electomate-backend  |     Connection._handle_dbapi_exception_noconnection(
electomate-backend  |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
electomate-backend  |         err, dialect, engine
electomate-backend  |         ^^^^^^^^^^^^^^^^^^^^
electomate-backend  |     )
electomate-backend  |     ^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 2440, in _handle_dbapi_exception_noconnection
electomate-backend  |     raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 143, in __init__
electomate-backend  |     self._dbapi_connection = engine.raw_connection()
electomate-backend  |                              ~~~~~~~~~~~~~~~~~~~~~^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/base.py", line 3301, in raw_connection
electomate-backend  |     return self.pool.connect()
electomate-backend  |            ~~~~~~~~~~~~~~~~~^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 447, in connect
electomate-backend  |     return _ConnectionFairy._checkout(self)
electomate-backend  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 1264, in _checkout
electomate-backend  |     fairy = _ConnectionRecord.checkout(pool)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 716, in checkout
electomate-backend  |     with util.safe_reraise():
electomate-backend  |          ~~~~~~~~~~~~~~~~~^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
electomate-backend  |     raise exc_value.with_traceback(exc_tb)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 714, in checkout
electomate-backend  |     dbapi_connection = rec.get_connection()
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 836, in get_connection
electomate-backend  |     self.__connect()
electomate-backend  |     ~~~~~~~~~~~~~~^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 899, in __connect
electomate-backend  |     with util.safe_reraise():
electomate-backend  |          ~~~~~~~~~~~~~~~~~^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/util/langhelpers.py", line 224, in __exit__
electomate-backend  |     raise exc_value.with_traceback(exc_tb)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py", line 895, in __connect
electomate-backend  |     self.dbapi_connection = connection = pool._invoke_creator(self)
electomate-backend  |                                          ~~~~~~~~~~~~~~~~~~~~^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/create.py", line 661, in connect
electomate-backend  |     return dialect.connect(*cargs, **cparams)
electomate-backend  |            ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/engine/default.py", line 629, in connect
electomate-backend  |     return self.loaded_dbapi.connect(*cargs, **cparams)  # type: ignore[no-any-return]  # NOQA: E501
electomate-backend  |            ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/psycopg.py", line 733, in connect
electomate-backend  |     await_only(creator_fn(*arg, **kw))
electomate-backend  |     ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
electomate-backend  |     return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
electomate-backend  |            ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
electomate-backend  |     value = await result
electomate-backend  |             ^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/psycopg/connection_async.py", line 140, in connect
electomate-backend  |     raise last_ex.with_traceback(None)
electomate-backend  | sqlalchemy.exc.OperationalError: (psycopg.errors.ConnectionTimeout) connection timeout expired
electomate-backend  | (Background on this error at: https://sqlalche.me/e/20/e3q8)
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document e95737d2-0d21-4817-aaab-669bc1255d37 | extra={"X-Request-ID": "d9fd6046f2fc4ceaae94638d94b308f4", "X-Correlation-ID": "7fcddecd92bb4e0886d6afffd8316875", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:19:20.812842Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document cff61c3e-f849-4c33-9b4f-5aefee984060 | extra={"X-Request-ID": "213b9fb395c74b8881f001f24b5b627f", "X-Correlation-ID": "8817f7a96f674a33a4819e0efb86af56", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:19:20.814947Z"}
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 134127, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:63684", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "0b334eca80e54b8f9bcce3d4c40ffe22", "X-Correlation-ID": "4818a5d554974d3d8f82797ab32698f7", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-18T01:19:20.822341Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 9b03188c-a111-409a-a816-3f013f281bee | extra={"X-Request-ID": "0b334eca80e54b8f9bcce3d4c40ffe22", "X-Correlation-ID": "4818a5d554974d3d8f82797ab32698f7", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:19:20.824213Z"}
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Alternative_für_Deutschland_AFD2025.pdf
electomate-backend  | /app/.venv/lib/python3.13/site-packages/torch/utils/data/dataloader.py:666: UserWarning: 'pin_memory' argument is set as true but no accelerator is found, then device pinned memory won't be used.
electomate-backend  |   warnings.warn(warn_msg)
electomate-backend  | /app/.venv/lib/python3.13/site-packages/easyocr/recognition.py:60: DeprecationWarning: 'mode' parameter is deprecated and will be removed in Pillow 13 (2026-10-15)
electomate-backend  |   return Image.fromarray(img, 'L')
electomate-backend  | INFO [docling.document_converter] Finished converting document Alternative_für_Deutschland_AFD2025.pdf in 289.57 sec.
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Die_Linke_L25.pdf
electomate-backend  | /app/.venv/lib/python3.13/site-packages/docling_core/types/doc/document.py:2546: DeprecationWarning: ListItem parent must be a list group, creating one on the fly.
electomate-backend  |   warnings.warn(
electomate-backend  | INFO [docling.document_converter] Finished converting document Die_Linke_L25.pdf in 109.85 sec.
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing b50d81e8-2601-4dca-8bb4-143b578c87f8 | extra={"X-Request-ID": "d177cf191fe844119fa8f1cd91c6dff8", "X-Correlation-ID": "d225844a109246eba069d221ea329502", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:26:00.787187Z"}
electomate-backend  | INFO [api] 200 GET/openapi.json | extra={"time": 61, "status": 200, "method": "GET", "path": "/openapi.json", "query": "", "client_ip": "172.18.0.1:58712", "route": "fastapi.applications.openapi", "X-Request-ID": "ad6f839f36834e8aa481c02a3410c524", "X-Correlation-ID": "f37d747b4e8b43b2aa7098bad1bc7860", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-18T01:26:00.813442Z"}
electomate-backend  |       INFO   172.18.0.1:58712 - "GET /openapi.json HTTP/1.1" 200
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Freie_Demokratische_Partei_FDP25.pdf
electomate-backend  | INFO [docling.document_converter] Finished converting document Freie_Demokratische_Partei_FDP25.pdf in 132.68 sec.
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 676262, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:60646", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "755b6d5dfbd846dda5e0fd4995ea641e", "X-Correlation-ID": "2825a2726a0f49e2afcc587875233454", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-18T01:28:22.968842Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing cff61c3e-f849-4c33-9b4f-5aefee984060 | extra={"X-Request-ID": "213b9fb395c74b8881f001f24b5b627f", "X-Correlation-ID": "8817f7a96f674a33a4819e0efb86af56", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:28:23.015906Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing e95737d2-0d21-4817-aaab-669bc1255d37 | extra={"X-Request-ID": "d9fd6046f2fc4ceaae94638d94b308f4", "X-Correlation-ID": "7fcddecd92bb4e0886d6afffd8316875", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:28:23.044819Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 23690bdd-3782-4f0f-82d4-d0b7f8300700 | extra={"X-Request-ID": "755b6d5dfbd846dda5e0fd4995ea641e", "X-Correlation-ID": "2825a2726a0f49e2afcc587875233454", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:28:23.069312Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking b50d81e8-2601-4dca-8bb4-143b578c87f8 | extra={"X-Request-ID": "d177cf191fe844119fa8f1cd91c6dff8", "X-Correlation-ID": "d225844a109246eba069d221ea329502", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:28:23.088603Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | ERROR [weaviate-client] {'message': 'Failed to send all objects in a batch of 20', 'error': 'WeaviateInsertManyAllFailedError("Every object failed during insertion. Here is the set of all errors: connection to: OpenAI API failed with status: 400 request-id: req_90bbf0916b6247008ff7ec7aaedd0d8a error: This model\'s maximum context length is 8192 tokens, however you requested 9415 tokens (9415 in your prompt; 0 for the completion). Please reduce your prompt; or completion length.")'}
electomate-backend  | ERROR [weaviate-client] {'message': 'Failed to send 20 objects in a batch of 20. Please inspect client.batch.failed_objects or collection.batch.failed_objects for the failed objects.'}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 9b03188c-a111-409a-a816-3f013f281bee | extra={"X-Request-ID": "0b334eca80e54b8f9bcce3d4c40ffe22", "X-Correlation-ID": "4818a5d554974d3d8f82797ab32698f7", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:28:39.536310Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking cff61c3e-f849-4c33-9b4f-5aefee984060 | extra={"X-Request-ID": "213b9fb395c74b8881f001f24b5b627f", "X-Correlation-ID": "8817f7a96f674a33a4819e0efb86af56", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:28:39.931817Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking e95737d2-0d21-4817-aaab-669bc1255d37 | extra={"X-Request-ID": "d9fd6046f2fc4ceaae94638d94b308f4", "X-Correlation-ID": "7fcddecd92bb4e0886d6afffd8316875", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:28:39.944620Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Bündnis_90_Die_Grünen_GR2025.pdf
electomate-backend  | /app/.venv/lib/python3.13/site-packages/torch/utils/data/dataloader.py:666: UserWarning: 'pin_memory' argument is set as true but no accelerator is found, then device pinned memory won't be used.
electomate-backend  |   warnings.warn(warn_msg)
electomate-backend  | /app/.venv/lib/python3.13/site-packages/easyocr/recognition.py:60: DeprecationWarning: 'mode' parameter is deprecated and will be removed in Pillow 13 (2026-10-15)
electomate-backend  |   return Image.fromarray(img, 'L')
electomate-backend  | /app/.venv/lib/python3.13/site-packages/torch/utils/data/dataloader.py:666: UserWarning: 'pin_memory' argument is set as true but no accelerator is found, then device pinned memory won't be used.
electomate-backend  |   warnings.warn(warn_msg)
electomate-backend  | /app/.venv/lib/python3.13/site-packages/easyocr/recognition.py:60: DeprecationWarning: 'mode' parameter is deprecated and will be removed in Pillow 13 (2026-10-15)
electomate-backend  |   return Image.fromarray(img, 'L')
electomate-backend  | INFO [docling.document_converter] Finished converting document Bündnis_90_Die_Grünen_GR2025.pdf in 274.66 sec.
electomate-backend  | /app/.venv/lib/python3.13/site-packages/docling/datamodel/base_models.py:406: RuntimeWarning: Mean of empty slice
electomate-backend  |   np.nanmean(
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 9b03188c-a111-409a-a816-3f013f281bee | extra={"X-Request-ID": "0b334eca80e54b8f9bcce3d4c40ffe22", "X-Correlation-ID": "4818a5d554974d3d8f82797ab32698f7", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:33:21.227558Z"}
electomate-backend  | INFO [api] 200 GET/v2/parties/?skip=0&limit=100 | extra={"time": 41, "status": 200, "method": "GET", "path": "/v2/parties/", "query": "skip=0&limit=100", "client_ip": "172.18.0.1:61030", "route": "em_backend.api.routers.parties.read_parties", "X-Request-ID": "30f8bc0a3fd54582b7a1654f321d276a", "X-Correlation-ID": "a832320f984a4f97b1c2e8fcebda4b26", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-18T01:33:21.278608Z"}
electomate-backend  |       INFO   172.18.0.1:61030 - "GET /v2/parties/?skip=0&limit=100 HTTP/1.1" 200
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 23690bdd-3782-4f0f-82d4-d0b7f8300700 | extra={"X-Request-ID": "755b6d5dfbd846dda5e0fd4995ea641e", "X-Correlation-ID": "2825a2726a0f49e2afcc587875233454", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:33:21.309570Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 23690bdd-3782-4f0f-82d4-d0b7f8300700 | extra={"X-Request-ID": "755b6d5dfbd846dda5e0fd4995ea641e", "X-Correlation-ID": "2825a2726a0f49e2afcc587875233454", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-18T01:33:24.572620Z"}
electomate-bac
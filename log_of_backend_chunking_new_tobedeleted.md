electomate-backend  | ERROR [api] 409 POST/v2/countries/ | extra={"time": 83, "status": 409, "method": "POST", "path": "/v2/countries/", "query": "", "client_ip": "172.18.0.1:62888", "route": "em_backend.api.routers.countries.create_country", "X-Request-ID": "582719cb1c5048289d0462f1123b3573", "X-Correlation-ID": "593842aa57534f8ea5ee1add4fe6937d", "span": null, "logger": "api", "level": "error", "timestamp": "2025-10-20T09:45:49.226728Z"}
electomate-backend  |       INFO   172.18.0.1:62888 - "POST /v2/countries/ HTTP/1.1" 409
electomate-backend  | INFO [api] 200 POST/v2/countries/ | extra={"time": 123, "status": 200, "method": "POST", "path": "/v2/countries/", "query": "", "client_ip": "172.18.0.1:62952", "route": "em_backend.api.routers.countries.create_country", "X-Request-ID": "b2da6515c75d47ffa87d0f41d048f54a", "X-Correlation-ID": "acbce46f0c324681b68a605ca64fc410", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:27.564932Z"}
electomate-backend  |       INFO   172.18.0.1:62952 - "POST /v2/countries/ HTTP/1.1" 200
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [api] 200 POST/v2/elections/ | extra={"time": 738, "status": 200, "method": "POST", "path": "/v2/elections/", "query": "", "client_ip": "172.18.0.1:62954", "route": "em_backend.api.routers.elections.create_election", "X-Request-ID": "8118ff4d2dda41b893aafa0c7fa86380", "X-Correlation-ID": "dc721a37f94c48709ac078b1d70fe0e9", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.339730Z"}
electomate-backend  |       INFO   172.18.0.1:62954 - "POST /v2/elections/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 GET/v2/parties/?skip=0&limit=1000 | extra={"time": 11, "status": 200, "method": "GET", "path": "/v2/parties/", "query": "skip=0&limit=1000", "client_ip": "172.18.0.1:62950", "route": "em_backend.api.routers.parties.read_parties", "X-Request-ID": "df8ff2b9e6204e04b0749ddb39ea81bc", "X-Correlation-ID": "54031f6035064bbdbe6e40daefba2308", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.364223Z"}
electomate-backend  |       INFO   172.18.0.1:62950 - "GET /v2/parties/?skip=0&limit=1000 HTTP/1.1"   
electomate-backend  |              200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 28, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62958", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "16669308d67b4288ac8e60719051eead", "X-Correlation-ID": "aa37d646520946f797cb76c65e2f51d8", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.407799Z"}
electomate-backend  |       INFO   172.18.0.1:62958 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 10, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62972", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "c27712bb44ce4d5ab200033fe9306aec", "X-Correlation-ID": "88b1c9ffef41493bb49f659585002267", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.431825Z"}
electomate-backend  |       INFO   172.18.0.1:62972 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 5, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62976", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "7e46b2bd277d4f0ba794ba853866240b", "X-Correlation-ID": "96fbea4aa9fd4cea94d8058f24ebed42", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.447769Z"}
electomate-backend  |       INFO   172.18.0.1:62976 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 4, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62990", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "eaed1b86cc3544e2aded6f7fe79e835c", "X-Correlation-ID": "62fcc10e1f3d4a75bb3a1498556f33b9", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.462185Z"}
electomate-backend  |       INFO   172.18.0.1:62990 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 3, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62998", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "3dd45f48ac25498f87f3ba4b9ebe7698", "X-Correlation-ID": "d632a76c97884c28aa0d0acb17173c86", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.475575Z"}
electomate-backend  |       INFO   172.18.0.1:62998 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 5, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:63004", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "75983cbebd06457f8852a045f7c5160f", "X-Correlation-ID": "9e13f9a782254618af27a06a554d6f19", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.489096Z"}
electomate-backend  |       INFO   172.18.0.1:63004 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 GET/v2/countries/?skip=0&limit=100 | extra={"time": 24, "status": 200, "method": "GET", "path": "/v2/countries/", "query": "skip=0&limit=100", "client_ip": "172.18.0.1:58978", "route": "em_backend.api.routers.countries.read_countries", "X-Request-ID": "a26d8afe5dd64bcc97ea2790e37dedb9", "X-Correlation-ID": "182dfb0a396943baa08e09005913282d", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:47:11.819034Z"}
electomate-backend  |       INFO   172.18.0.1:58978 - "GET /v2/countries/?skip=0&limit=100 HTTP/1.1"  
electomate-backend  |              200
electomate-backend  | INFO [api] 200 GET/v2/elections/?skip=0&limit=100 | extra={"time": 28, "status": 200, "method": "GET", "path": "/v2/elections/", "query": "skip=0&limit=100", "client_ip": "172.18.0.1:63608", "route": "em_backend.api.routers.elections.read_elections", "X-Request-ID": "9ca64efc6f2b4e4db8bf7f96cc49681b", "X-Correlation-ID": "69deef0c7c5a44ed907fb1cf7fbd9fce", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:47:48.906644Z"}
electomate-backend  |       INFO   172.18.0.1:63608 - "GET /v2/elections/?skip=0&limit=100 HTTP/1.1"  
electomate-backend  |              200
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 469, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:60632", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:48:22.202959Z"}
electomate-backend  |       INFO   172.18.0.1:60632 - "POST /v2/documents/ HTTP/1.1" 200
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 40aa6d11-c77e-40d2-ab20-f014bf774643 | extra={"X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:48:22.233223Z"}
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Christlich_Demokratische_Union_Deutschlands_CDU25.pdf
electomate-backend  | INFO [docling.document_converter] Finished converting document Christlich_Demokratische_Union_Deutschlands_CDU25.pdf in 257.66 sec.
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 40aa6d11-c77e-40d2-ab20-f014bf774643 | extra={"X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:52:40.320159Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "40aa6d11-c77e-40d2-ab20-f014bf774643", "processed_chunks": 114, "X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T09:52:45.279310Z"}
electomate-backend  | ERROR [api] 400 POST/v2/documents/ | extra={"time": 5034, "status": 400, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:63730", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "49000b9c46574043ba4cd81173be3061", "X-Correlation-ID": "6effea463d7242ac9b98c9a1f79c1a9a", "span": null, "logger": "api", "level": "error", "timestamp": "2025-10-20T09:52:45.295014Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 40aa6d11-c77e-40d2-ab20-f014bf774643 | extra={"X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:52:45.366950Z"}
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 263149, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:60636", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:52:45.423912Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 055e38b5-ed08-4ddb-9fd4-7799d603feb3 | extra={"X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:52:45.429428Z"}
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Sozialdemokratische_Partei_Deutschlands_SPD25.pdf
electomate-backend  | /app/.venv/lib/python3.13/site-packages/docling_parse/pdf_parser.py:162: ResourceWarning: Unclosed file <tempfile.SpooledTemporaryFile object at 0xffff1e1f7eb0>
electomate-backend  |   doc_dict = self._parser.parse_pdf_from_key_on_page(
electomate-backend  | ResourceWarning: Enable tracemalloc to get the object allocation traceback
electomate-backend  | 2025-10-20 09:55:14,994 - INFO - 2 changes detected
electomate-backend  |    WARNING   WatchFiles detected changes in 'src/em_backend/vector/parser.py'.  
electomate-backend  |              Reloading...
electomate-backend  | 2025-10-20 09:55:15,070 - WARNING - WatchFiles detected changes in 'src/em_backend/vector/parser.py'. Reloading...
electomate-backend  | INFO [docling.document_converter] Finished converting document Sozialdemokratische_Partei_Deutschlands_SPD25.pdf in 233.50 sec.
electomate-backend  | /app/.venv/lib/python3.13/site-packages/docling/datamodel/base_models.py:406: RuntimeWarning: Mean of empty slice
electomate-backend  |   np.nanmean(
electomate-backend  | INFO [uvicorn.error] Shutting down
electomate-backend  |       INFO   Shutting down
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 238921, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:59168", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "7c6fa816b8c2499fb982ec00542bccab", "X-Correlation-ID": "f5a08fb23d63442c80cf7c897eddd300", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:56:39.207372Z"}
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 238957, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:60566", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "b90defe16e20489c9e29f4e2cd873755", "X-Correlation-ID": "ab1c6432d9cc44ae9c033e7d5f80e5d2", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:56:39.212844Z"}
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 238935, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:57214", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "c11ef322782847668cfead3857f2112a", "X-Correlation-ID": "0d7a77394892461280ea72364a9416af", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:56:39.213829Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document dad78a54-63b7-4506-b052-8331757ffab2 | extra={"X-Request-ID": "7c6fa816b8c2499fb982ec00542bccab", "X-Correlation-ID": "f5a08fb23d63442c80cf7c897eddd300", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:56:39.215463Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 3826a4e3-998a-496b-a04f-15f7ea89f9f2 | extra={"X-Request-ID": "b90defe16e20489c9e29f4e2cd873755", "X-Correlation-ID": "ab1c6432d9cc44ae9c033e7d5f80e5d2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:56:39.217738Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 2761115a-d728-4b9e-a294-1f77bdb4e539 | extra={"X-Request-ID": "c11ef322782847668cfead3857f2112a", "X-Correlation-ID": "0d7a77394892461280ea72364a9416af", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:56:39.218387Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 055e38b5-ed08-4ddb-9fd4-7799d603feb3 | extra={"X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:56:39.232150Z"}
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Alternative_für_Deutschland_AFD2025.pdf
electomate-backend  | /app/.venv/lib/python3.13/site-packages/torch/utils/data/dataloader.py:666: UserWarning: 'pin_memory' argument is set as true but no accelerator is found, then device pinned memory won't be used.
electomate-backend  |   warnings.warn(warn_msg)
electomate-backend  | /app/.venv/lib/python3.13/site-packages/easyocr/recognition.py:60: DeprecationWarning: 'mode' parameter is deprecated and will be removed in Pillow 13 (2026-10-15)
electomate-backend  |   return Image.fromarray(img, 'L')
electomate-backend  | INFO [docling.document_converter] Finished converting document Alternative_für_Deutschland_AFD2025.pdf in 353.76 sec.
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Die_Linke_L25.pdf
electomate-backend  | /app/.venv/lib/python3.13/site-packages/docling_core/types/doc/document.py:2546: DeprecationWarning: ListItem parent must be a list group, creating one on the fly.
electomate-backend  |   warnings.warn(
electomate-backend  | INFO [docling.document_converter] Finished converting document Die_Linke_L25.pdf in 156.90 sec.
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "055e38b5-ed08-4ddb-9fd4-7799d603feb3", "processed_chunks": 104, "X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T10:05:15.555970Z"}
electomate-backend  | INFO [uvicorn.error] Waiting for background tasks to complete. (CTRL+C to force quit)
electomate-backend  |       INFO   Waiting for background tasks to complete. (CTRL+C to force quit)
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 055e38b5-ed08-4ddb-9fd4-7799d603feb3 | extra={"X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T10:05:15.608639Z"}
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Freie_Demokratische_Partei_FDP25.pdf





all the logs: 

electomate-backend  | ERROR [api] 409 POST/v2/countries/ | extra={"time": 83, "status": 409, "method": "POST", "path": "/v2/countries/", "query": "", "client_ip": "172.18.0.1:62888", "route": "em_backend.api.routers.countries.create_country", "X-Request-ID": "582719cb1c5048289d0462f1123b3573", "X-Correlation-ID": "593842aa57534f8ea5ee1add4fe6937d", "span": null, "logger": "api", "level": "error", "timestamp": "2025-10-20T09:45:49.226728Z"}
electomate-backend  |       INFO   172.18.0.1:62888 - "POST /v2/countries/ HTTP/1.1" 409
electomate-backend  | INFO [api] 200 POST/v2/countries/ | extra={"time": 123, "status": 200, "method": "POST", "path": "/v2/countries/", "query": "", "client_ip": "172.18.0.1:62952", "route": "em_backend.api.routers.countries.create_country", "X-Request-ID": "b2da6515c75d47ffa87d0f41d048f54a", "X-Correlation-ID": "acbce46f0c324681b68a605ca64fc410", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:27.564932Z"}
electomate-backend  |       INFO   172.18.0.1:62952 - "POST /v2/countries/ HTTP/1.1" 200
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [api] 200 POST/v2/elections/ | extra={"time": 738, "status": 200, "method": "POST", "path": "/v2/elections/", "query": "", "client_ip": "172.18.0.1:62954", "route": "em_backend.api.routers.elections.create_election", "X-Request-ID": "8118ff4d2dda41b893aafa0c7fa86380", "X-Correlation-ID": "dc721a37f94c48709ac078b1d70fe0e9", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.339730Z"}
electomate-backend  |       INFO   172.18.0.1:62954 - "POST /v2/elections/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 GET/v2/parties/?skip=0&limit=1000 | extra={"time": 11, "status": 200, "method": "GET", "path": "/v2/parties/", "query": "skip=0&limit=1000", "client_ip": "172.18.0.1:62950", "route": "em_backend.api.routers.parties.read_parties", "X-Request-ID": "df8ff2b9e6204e04b0749ddb39ea81bc", "X-Correlation-ID": "54031f6035064bbdbe6e40daefba2308", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.364223Z"}
electomate-backend  |       INFO   172.18.0.1:62950 - "GET /v2/parties/?skip=0&limit=1000 HTTP/1.1"   
electomate-backend  |              200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 28, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62958", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "16669308d67b4288ac8e60719051eead", "X-Correlation-ID": "aa37d646520946f797cb76c65e2f51d8", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.407799Z"}
electomate-backend  |       INFO   172.18.0.1:62958 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 10, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62972", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "c27712bb44ce4d5ab200033fe9306aec", "X-Correlation-ID": "88b1c9ffef41493bb49f659585002267", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.431825Z"}
electomate-backend  |       INFO   172.18.0.1:62972 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 5, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62976", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "7e46b2bd277d4f0ba794ba853866240b", "X-Correlation-ID": "96fbea4aa9fd4cea94d8058f24ebed42", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.447769Z"}
electomate-backend  |       INFO   172.18.0.1:62976 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 4, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62990", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "eaed1b86cc3544e2aded6f7fe79e835c", "X-Correlation-ID": "62fcc10e1f3d4a75bb3a1498556f33b9", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.462185Z"}
electomate-backend  |       INFO   172.18.0.1:62990 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 3, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:62998", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "3dd45f48ac25498f87f3ba4b9ebe7698", "X-Correlation-ID": "d632a76c97884c28aa0d0acb17173c86", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.475575Z"}
electomate-backend  |       INFO   172.18.0.1:62998 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 POST/v2/parties/ | extra={"time": 5, "status": 200, "method": "POST", "path": "/v2/parties/", "query": "", "client_ip": "172.18.0.1:63004", "route": "em_backend.api.routers.parties.create_party", "X-Request-ID": "75983cbebd06457f8852a045f7c5160f", "X-Correlation-ID": "9e13f9a782254618af27a06a554d6f19", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:46:28.489096Z"}
electomate-backend  |       INFO   172.18.0.1:63004 - "POST /v2/parties/ HTTP/1.1" 200
electomate-backend  | INFO [api] 200 GET/v2/countries/?skip=0&limit=100 | extra={"time": 24, "status": 200, "method": "GET", "path": "/v2/countries/", "query": "skip=0&limit=100", "client_ip": "172.18.0.1:58978", "route": "em_backend.api.routers.countries.read_countries", "X-Request-ID": "a26d8afe5dd64bcc97ea2790e37dedb9", "X-Correlation-ID": "182dfb0a396943baa08e09005913282d", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:47:11.819034Z"}
electomate-backend  |       INFO   172.18.0.1:58978 - "GET /v2/countries/?skip=0&limit=100 HTTP/1.1"  
electomate-backend  |              200
electomate-backend  | INFO [api] 200 GET/v2/elections/?skip=0&limit=100 | extra={"time": 28, "status": 200, "method": "GET", "path": "/v2/elections/", "query": "skip=0&limit=100", "client_ip": "172.18.0.1:63608", "route": "em_backend.api.routers.elections.read_elections", "X-Request-ID": "9ca64efc6f2b4e4db8bf7f96cc49681b", "X-Correlation-ID": "69deef0c7c5a44ed907fb1cf7fbd9fce", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:47:48.906644Z"}
electomate-backend  |       INFO   172.18.0.1:63608 - "GET /v2/elections/?skip=0&limit=100 HTTP/1.1"  
electomate-backend  |              200
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 469, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:60632", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:48:22.202959Z"}
electomate-backend  |       INFO   172.18.0.1:60632 - "POST /v2/documents/ HTTP/1.1" 200
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 40aa6d11-c77e-40d2-ab20-f014bf774643 | extra={"X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:48:22.233223Z"}
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Christlich_Demokratische_Union_Deutschlands_CDU25.pdf
electomate-backend  | INFO [docling.document_converter] Finished converting document Christlich_Demokratische_Union_Deutschlands_CDU25.pdf in 257.66 sec.
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 40aa6d11-c77e-40d2-ab20-f014bf774643 | extra={"X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:52:40.320159Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "40aa6d11-c77e-40d2-ab20-f014bf774643", "processed_chunks": 114, "X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T09:52:45.279310Z"}
electomate-backend  | ERROR [api] 400 POST/v2/documents/ | extra={"time": 5034, "status": 400, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:63730", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "49000b9c46574043ba4cd81173be3061", "X-Correlation-ID": "6effea463d7242ac9b98c9a1f79c1a9a", "span": null, "logger": "api", "level": "error", "timestamp": "2025-10-20T09:52:45.295014Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 40aa6d11-c77e-40d2-ab20-f014bf774643 | extra={"X-Request-ID": "008b5c71513b4777ad0558dd8e1f1229", "X-Correlation-ID": "becb368322af4a91a797f55cfd9d9ec2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:52:45.366950Z"}
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 263149, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:60636", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:52:45.423912Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 055e38b5-ed08-4ddb-9fd4-7799d603feb3 | extra={"X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:52:45.429428Z"}
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Sozialdemokratische_Partei_Deutschlands_SPD25.pdf
electomate-backend  | /app/.venv/lib/python3.13/site-packages/docling_parse/pdf_parser.py:162: ResourceWarning: Unclosed file <tempfile.SpooledTemporaryFile object at 0xffff1e1f7eb0>
electomate-backend  |   doc_dict = self._parser.parse_pdf_from_key_on_page(
electomate-backend  | ResourceWarning: Enable tracemalloc to get the object allocation traceback
electomate-backend  | 2025-10-20 09:55:14,994 - INFO - 2 changes detected
electomate-backend  |    WARNING   WatchFiles detected changes in 'src/em_backend/vector/parser.py'.  
electomate-backend  |              Reloading...
electomate-backend  | 2025-10-20 09:55:15,070 - WARNING - WatchFiles detected changes in 'src/em_backend/vector/parser.py'. Reloading...
electomate-backend  | INFO [docling.document_converter] Finished converting document Sozialdemokratische_Partei_Deutschlands_SPD25.pdf in 233.50 sec.
electomate-backend  | /app/.venv/lib/python3.13/site-packages/docling/datamodel/base_models.py:406: RuntimeWarning: Mean of empty slice
electomate-backend  |   np.nanmean(
electomate-backend  | INFO [uvicorn.error] Shutting down
electomate-backend  |       INFO   Shutting down
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 238921, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:59168", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "7c6fa816b8c2499fb982ec00542bccab", "X-Correlation-ID": "f5a08fb23d63442c80cf7c897eddd300", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:56:39.207372Z"}
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 238957, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:60566", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "b90defe16e20489c9e29f4e2cd873755", "X-Correlation-ID": "ab1c6432d9cc44ae9c033e7d5f80e5d2", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:56:39.212844Z"}
electomate-backend  | INFO [api] 200 POST/v2/documents/ | extra={"time": 238935, "status": 200, "method": "POST", "path": "/v2/documents/", "query": "", "client_ip": "172.18.0.1:57214", "route": "em_backend.api.routers.documents.create_document", "X-Request-ID": "c11ef322782847668cfead3857f2112a", "X-Correlation-ID": "0d7a77394892461280ea72364a9416af", "span": null, "logger": "api", "level": "info", "timestamp": "2025-10-20T09:56:39.213829Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document dad78a54-63b7-4506-b052-8331757ffab2 | extra={"X-Request-ID": "7c6fa816b8c2499fb982ec00542bccab", "X-Correlation-ID": "f5a08fb23d63442c80cf7c897eddd300", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:56:39.215463Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 3826a4e3-998a-496b-a04f-15f7ea89f9f2 | extra={"X-Request-ID": "b90defe16e20489c9e29f4e2cd873755", "X-Correlation-ID": "ab1c6432d9cc44ae9c033e7d5f80e5d2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:56:39.217738Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Started processing document 2761115a-d728-4b9e-a294-1f77bdb4e539 | extra={"X-Request-ID": "c11ef322782847668cfead3857f2112a", "X-Correlation-ID": "0d7a77394892461280ea72364a9416af", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:56:39.218387Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 055e38b5-ed08-4ddb-9fd4-7799d603feb3 | extra={"X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T09:56:39.232150Z"}
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Alternative_für_Deutschland_AFD2025.pdf
electomate-backend  | /app/.venv/lib/python3.13/site-packages/torch/utils/data/dataloader.py:666: UserWarning: 'pin_memory' argument is set as true but no accelerator is found, then device pinned memory won't be used.
electomate-backend  |   warnings.warn(warn_msg)
electomate-backend  | /app/.venv/lib/python3.13/site-packages/easyocr/recognition.py:60: DeprecationWarning: 'mode' parameter is deprecated and will be removed in Pillow 13 (2026-10-15)
electomate-backend  |   return Image.fromarray(img, 'L')
electomate-backend  | INFO [docling.document_converter] Finished converting document Alternative_für_Deutschland_AFD2025.pdf in 353.76 sec.
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Die_Linke_L25.pdf
electomate-backend  | /app/.venv/lib/python3.13/site-packages/docling_core/types/doc/document.py:2546: DeprecationWarning: ListItem parent must be a list group, creating one on the fly.
electomate-backend  |   warnings.warn(
electomate-backend  | INFO [docling.document_converter] Finished converting document Die_Linke_L25.pdf in 156.90 sec.
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "055e38b5-ed08-4ddb-9fd4-7799d603feb3", "processed_chunks": 104, "X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T10:05:15.555970Z"}
electomate-backend  | INFO [uvicorn.error] Waiting for background tasks to complete. (CTRL+C to force quit)
electomate-backend  |       INFO   Waiting for background tasks to complete. (CTRL+C to force quit)
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 055e38b5-ed08-4ddb-9fd4-7799d603feb3 | extra={"X-Request-ID": "7576720beafa46d2bfa7fae26d664fe2", "X-Correlation-ID": "b25e829ff3284d9daef4c784612b773c", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T10:05:15.608639Z"}
electomate-backend  | INFO [docling.datamodel.document] detected formats: [<InputFormat.PDF: 'pdf'>]
electomate-backend  | INFO [docling.document_converter] Going to convert document batch...
electomate-backend  | INFO [docling.pipeline.base_pipeline] Processing document Freie_Demokratische_Partei_FDP25.pdf
electomate-backend  | INFO [docling.document_converter] Finished converting document Freie_Demokratische_Partei_FDP25.pdf in 121.42 sec.
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 3826a4e3-998a-496b-a04f-15f7ea89f9f2 | extra={"X-Request-ID": "b90defe16e20489c9e29f4e2cd873755", "X-Correlation-ID": "ab1c6432d9cc44ae9c033e7d5f80e5d2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T10:07:17.267307Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 2761115a-d728-4b9e-a294-1f77bdb4e539 | extra={"X-Request-ID": "c11ef322782847668cfead3857f2112a", "X-Correlation-ID": "0d7a77394892461280ea72364a9416af", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T10:07:17.279133Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "3826a4e3-998a-496b-a04f-15f7ea89f9f2", "processed_chunks": 189, "X-Request-ID": "b90defe16e20489c9e29f4e2cd873755", "X-Correlation-ID": "ab1c6432d9cc44ae9c033e7d5f80e5d2", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T10:07:27.763696Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | ERROR [weaviate-client] {'message': 'Failed to send all objects in a batch of 20', 'error': 'WeaviateInsertManyAllFailedError("Every object failed during insertion. Here is the set of all errors: connection to: OpenAI API failed with status: 400 request-id: req_2e49359fd8d542bd8d03ddd0d6e10521 error: This model\'s maximum context length is 8192 tokens, however you requested 9415 tokens (9415 in your prompt; 0 for the completion). Please reduce your prompt; or completion length.")'}
electomate-backend  | ERROR [weaviate-client] {'message': 'Failed to send 20 objects in a batch of 20. Please inspect client.batch.failed_objects or collection.batch.failed_objects for the failed objects.'}
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "2761115a-d728-4b9e-a294-1f77bdb4e539", "processed_chunks": 20, "X-Request-ID": "c11ef322782847668cfead3857f2112a", "X-Correlation-ID": "0d7a77394892461280ea72364a9416af", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T10:07:32.880177Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 2761115a-d728-4b9e-a294-1f77bdb4e539 | extra={"X-Request-ID": "c11ef322782847668cfead3857f2112a", "X-Correlation-ID": "0d7a77394892461280ea72364a9416af", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T10:07:32.912121Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 3826a4e3-998a-496b-a04f-15f7ea89f9f2 | extra={"X-Request-ID": "b90defe16e20489c9e29f4e2cd873755", "X-Correlation-ID": "ab1c6432d9cc44ae9c033e7d5f80e5d2", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T10:07:32.913366Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing dad78a54-63b7-4506-b052-8331757ffab2 | extra={"X-Request-ID": "7c6fa816b8c2499fb982ec00542bccab", "X-Correlation-ID": "f5a08fb23d63442c80cf7c897eddd300", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T10:07:32.925765Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahl "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "dad78a54-63b7-4506-b052-8331757ffab2", "processed_chunks": 125, "X-Request-ID": "7c6fa816b8c2499fb982ec00542bccab", "X-Correlation-ID": "f5a08fb23d63442c80cf7c897eddd300", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T10:07:36.598840Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking dad78a54-63b7-4506-b052-8331757ffab2 | extra={"X-Request-ID": "7c6fa816b8c2499fb982ec00542bccab", "X-Correlation-ID": "f5a08fb23d63442c80cf7c897eddd300", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T10:07:36.623375Z"}
electomate-backend  | INFO [uvicorn.error] Waiting for application shutdown.
electomate-backend  |       INFO   Waiting for application shutdown.
electomate-backend  |       INFO   Application shutdown complete.
electomate-backend  | INFO [uvicorn.error] Application shutdown complete.
electomate-backend  | INFO [uvicorn.error] Finished server process [51923]
electomate-backend  |       INFO   Finished server process [51923]
electomate-backend  | 2025-10-20 10:07:37,464 - INFO - 4 changes detected
electomate-backend  |    WARNING   WatchFiles detected changes in 'src/em_backend/vector/parser.py'.  
electomate-backend  |              Reloading...
electomate-backend  | 2025-10-20 10:07:37,484 - WARNING - WatchFiles detected changes in 'src/em_backend/vector/parser.py'. Reloading...
electomate-backend  | 2025-10-20 10:07:46,998 - INFO - 3 changes detected
electomate-backend  |       INFO   Started server process [532]
electomate-backend  | 2025-10-20 10:07:52,830 - INFO - Started server process [532]
electomate-backend  |       INFO   Waiting for application startup.
electomate-backend  | 2025-10-20 10:07:52,838 - INFO - Waiting for application startup.
electomate-backend  | INFO [em_backend.api.routers.v2] Initializing Perplexity client with model='sonar'
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/meta "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://pypi.org/pypi/weaviate-client/json "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/meta "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://pypi.org/pypi/weaviate-client/json "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/.well-known/ready "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/.well-known/ready "HTTP/1.1 200 OK"
electomate-backend  |       INFO   Application startup complete.
electomate-backend  | INFO [uvicorn.error] Application startup complete.
electomate-backend  | 2025-10-20 10:10:11,145 - INFO - 2 changes detected
electomate-backend  |    WARNING   WatchFiles detected changes in                                     
electomate-backend  |              'src/em_backend/agent/prompts/single_party_answer.py'. Reloading...
electomate-backend  | 2025-10-20 10:10:11,177 - WARNING - WatchFiles detected changes in 'src/em_backend/agent/prompts/single_party_answer.py'. Reloading...
electomate-backend  |       INFO   Shutting down
electomate-backend  | INFO [uvicorn.error] Shutting down
electomate-backend  |       INFO   Waiting for application shutdown.
electomate-backend  | INFO [uvicorn.error] Waiting for application shutdown.
electomate-backend  | INFO [uvicorn.error] Application shutdown complete.
electomate-backend  |       INFO   Application shutdown complete.
electomate-backend  |       INFO   Finished server process [532]
electomate-backend  | INFO [uvicorn.error] Finished server process [532]
electomate-backend  | 2025-10-20 10:10:19,745 - INFO - 3 changes detected
electomate-backend  |       INFO   Started server process [599]
electomate-backend  | 2025-10-20 10:10:28,279 - INFO - Started server process [599]
electomate-backend  |       INFO   Waiting for application startup.
electomate-backend  | 2025-10-20 10:10:28,282 - INFO - Waiting for application startup.
electomate-backend  | INFO [em_backend.api.routers.v2] Initializing Perplexity client with model='sonar'
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/meta "HTTP/1.1 200 OK"
electomate-backend  | ERROR [uvicorn.error] Traceback (most recent call last):
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py", line 323, in _ping_grpc
electomate-backend  |     res = self._grpc_channel.unary_unary(
electomate-backend  |     ...<2 lines>...
electomate-backend  |         response_deserializer=health_weaviate_pb2.WeaviateHealthCheckResponse.FromString,
electomate-backend  |     )(health_weaviate_pb2.WeaviateHealthCheckRequest(), timeout=self.timeout_config.init)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/grpc/_channel.py", line 1181, in __call__
electomate-backend  |     return _end_unary_response_blocking(state, call, False, None)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/grpc/_channel.py", line 1009, in _end_unary_response_blocking
electomate-backend  |     raise _InactiveRpcError(state)  # pytype: disable=not-instantiable
electomate-backend  |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  | grpc._channel._InactiveRpcError: <_InactiveRpcError of RPC that terminated with:
electomate-backend  |   status = StatusCode.DEADLINE_EXCEEDED
electomate-backend  |   details = "Deadline Exceeded"
electomate-backend  |   debug_error_string = "UNKNOWN:Error received from peer  {grpc_status:4, grpc_message:"Deadline Exceeded"}"
electomate-backend  | >
electomate-backend  | 
electomate-backend  | The above exception was the direct cause of the following exception:
electomate-backend  | 
electomate-backend  | Traceback (most recent call last):
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/starlette/routing.py", line 694, in lifespan
electomate-backend  |     async with self.lifespan_context(app) as maybe_state:
electomate-backend  |                ~~~~~~~~~~~~~~~~~~~~~^^^^^
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 210, in merged_lifespan
electomate-backend  |     async with nested_context(app) as maybe_nested_state:
electomate-backend  |                ~~~~~~~~~~~~~~^^^^^
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 209, in merged_lifespan
electomate-backend  |     async with original_context(app) as maybe_original_state:
electomate-backend  |                ~~~~~~~~~~~~~~~~^^^^^
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 209, in merged_lifespan
electomate-backend  |     async with original_context(app) as maybe_original_state:
electomate-backend  |                ~~~~~~~~~~~~~~~~^^^^^
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |      ERROR   Traceback (most recent call last):                                 
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py",  
electomate-backend  |              line 323, in _ping_grpc                                            
electomate-backend  |                  res = self._grpc_channel.unary_unary(                          
electomate-backend  |                  ...<2 lines>...                                                
electomate-backend  |                      response_deserializer=health_weaviate_pb2.WeaviateHealthChe
electomate-backend  |              ckResponse.FromString,                                             
electomate-backend  |                  )(health_weaviate_pb2.WeaviateHealthCheckRequest(),            
electomate-backend  |              timeout=self.timeout_config.init)                                  
electomate-backend  |                File "/app/.venv/lib/python3.13/site-packages/grpc/_channel.py", 
electomate-backend  |              line 1181, in __call__                                             
electomate-backend  |                  return _end_unary_response_blocking(state, call, False, None)  
electomate-backend  |                File "/app/.venv/lib/python3.13/site-packages/grpc/_channel.py", 
electomate-backend  |              line 1009, in _end_unary_response_blocking                         
electomate-backend  |                  raise _InactiveRpcError(state)  # pytype:                      
electomate-backend  |              disable=not-instantiable                                           
electomate-backend  |                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                 
electomate-backend  |              grpc._channel._InactiveRpcError: <_InactiveRpcError of RPC that    
electomate-backend  |              terminated with:                                                   
electomate-backend  |                      status = StatusCode.DEADLINE_EXCEEDED                      
electomate-backend  |                      details = "Deadline Exceeded"                              
electomate-backend  |                      debug_error_string = "UNKNOWN:Error received from peer     
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 209, in merged_lifespan
electomate-backend  |     async with original_context(app) as maybe_original_state:
electomate-backend  |                ~~~~~~~~~~~~~~~~^^^^^
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 209, in merged_lifespan
electomate-backend  |     async with original_context(app) as maybe_original_state:
electomate-backend  |                ~~~~~~~~~~~~~~~~^^^^^
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 209, in merged_lifespan
electomate-backend  |     async with original_context(app) as maybe_original_state:
electomate-backend  |                ~~~~~~~~~~~~~~~~^^^^^
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 209, in merged_lifespan
electomate-backend  |     async with original_context(app) as maybe_original_state:
electomate-backend  |                ~~~~~~~~~~~~~~~~^^^^^
electomate-backend  |              {grpc_status:4, grpc_message:"Deadline Exceeded"}"                 
electomate-backend  |              >                                                                  
electomate-backend  |                                                                                 
electomate-backend  |              The above exception was the direct cause of the following          
electomate-backend  |              exception:                                                         
electomate-backend  |                                                                                 
electomate-backend  |              Traceback (most recent call last):                                 
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/starlette/routing.py",    
electomate-backend  |              line 694, in lifespan                                              
electomate-backend  |                  async with self.lifespan_context(app) as maybe_state:          
electomate-backend  |                             ~~~~~~~~~~~~~~~~~~~~~^^^^^                          
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 
electomate-backend  |              210, in merged_lifespan                                            
electomate-backend  |                  async with nested_context(app) as maybe_nested_state:          
electomate-backend  |                             ~~~~~~~~~~~~~~^^^^^                                 
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 209, in merged_lifespan
electomate-backend  |     async with original_context(app) as maybe_original_state:
electomate-backend  |                ~~~~~~~~~~~~~~~~^^^^^
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/src/em_backend/api/routers/v2.py", line 37, in lifespan
electomate-backend  |     VectorDatabase.create() as vector_database,
electomate-backend  |     ~~~~~~~~~~~~~~~~~~~~~^^
electomate-backend  |   File "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib.py", line 214, in __aenter__
electomate-backend  |     return await anext(self.gen)
electomate-backend  |            ^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |   File "/app/src/em_backend/vector/db.py", line 50, in create
electomate-backend  |     client = weaviate.connect_to_weaviate_cloud(
electomate-backend  |         cluster_url=settings.wv_url,
electomate-backend  |     ...<3 lines>...
electomate-backend  |         },
electomate-backend  |     )
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/helpers.py", line 107, in connect_to_weaviate_cloud
electomate-backend  |     return __connect(
electomate-backend  |         WeaviateClient(
electomate-backend  |     ...<8 lines>...
electomate-backend  |         )
electomate-backend  |     )
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/helpers.py", line 371, in __connect
electomate-backend  |     raise e
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/helpers.py", line 367, in __connect
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 
electomate-backend  |              209, in merged_lifespan                                            
electomate-backend  |                  async with original_context(app) as maybe_original_state:      
electomate-backend  |                             ~~~~~~~~~~~~~~~~^^^^^                               
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 
electomate-backend  |              209, in merged_lifespan                                            
electomate-backend  |                  async with original_context(app) as maybe_original_state:      
electomate-backend  |                             ~~~~~~~~~~~~~~~~^^^^^                               
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 
electomate-backend  |              209, in merged_lifespan                                            
electomate-backend  |                  async with original_context(app) as maybe_original_state:      
electomate-backend  |                             ~~~~~~~~~~~~~~~~^^^^^                               
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 
electomate-backend  |              209, in merged_lifespan                                            
electomate-backend  |     client.connect()
electomate-backend  |     ~~~~~~~~~~~~~~^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/client_executor.py", line 149, in connect
electomate-backend  |     return executor.execute(
electomate-backend  |            ~~~~~~~~~~~~~~~~^
electomate-backend  |         response_callback=lambda _: None,
electomate-backend  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |         method=self._connection.connect,
electomate-backend  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
electomate-backend  |     )
electomate-backend  |     ^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/executor.py", line 99, in execute
electomate-backend  |     return cast(T, exception_callback(e))
electomate-backend  |                    ~~~~~~~~~~~~~~~~~~^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/executor.py", line 38, in raise_exception
electomate-backend  |     raise e
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/executor.py", line 80, in execute
electomate-backend  |     call = method(*args, **kwargs)
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py", line 958, in connect
electomate-backend  |     raise e
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py", line 954, in connect
electomate-backend  |     executor.result(self._ping_grpc("sync"))
electomate-backend  |                     ~~~~~~~~~~~~~~~^^^^^^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py", line 345, in _ping_grpc
electomate-backend  |     self.__handle_ping_exception(e)
electomate-backend  |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^
electomate-backend  |   File "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py", line 356, in __handle_ping_exception
electomate-backend  |     raise WeaviateGRPCUnavailableError(
electomate-backend  |         f"v{self.server_version}", self._connection_params._grpc_address
electomate-backend  |     ) from e
electomate-backend  | weaviate.exceptions.WeaviateGRPCUnavailableError: 
electomate-backend  | Weaviate v1.32.10 makes use of a high-speed gRPC API as well as a REST API.
electomate-backend  | Unfortunately, the gRPC health check against Weaviate could not be completed.
electomate-backend  | 
electomate-backend  | This error could be due to one of several reasons:
electomate-backend  | - The gRPC traffic at the specified port is blocked by a firewall.
electomate-backend  | - gRPC is not enabled or incorrectly configured on the server or the client.
electomate-backend  |     - Please check that the server address and port (grpc-rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud:443) are correct.
electomate-backend  | - your connection is unstable or has a high latency. In this case you can:
electomate-backend  |     - increase init-timeout in `weaviate.connect_to_local(additional_config=wvc.init.AdditionalConfig(timeout=wvc.init.Timeout(init=X)))`
electomate-backend  |     - disable startup checks by connecting using `skip_init_checks=True`
electomate-backend  |                  async with original_context(app) as maybe_original_state:      
electomate-backend  |                             ~~~~~~~~~~~~~~~~^^^^^                               
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 
electomate-backend  |              209, in merged_lifespan                                            
electomate-backend  |                  async with original_context(app) as maybe_original_state:      
electomate-backend  |                             ~~~~~~~~~~~~~~~~^^^^^                               
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 
electomate-backend  |              209, in merged_lifespan                                            
electomate-backend  |                  async with original_context(app) as maybe_original_state:      
electomate-backend  |                             ~~~~~~~~~~~~~~~~^^^^^                               
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 
electomate-backend  | 
electomate-backend  | 
electomate-backend  | ERROR [uvicorn.error] Application startup failed. Exiting.
electomate-backend  |              209, in merged_lifespan                                            
electomate-backend  |                  async with original_context(app) as maybe_original_state:      
electomate-backend  |                             ~~~~~~~~~~~~~~~~^^^^^                               
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File "/app/src/em_backend/api/routers/v2.py", line 37, in        
electomate-backend  |              lifespan                                                           
electomate-backend  |                  VectorDatabase.create() as vector_database,                    
electomate-backend  |                  ~~~~~~~~~~~~~~~~~~~~~^^                                        
electomate-backend  |                File                                                             
electomate-backend  |              "/python/cpython-3.13.9-linux-aarch64-gnu/lib/python3.13/contextlib
electomate-backend  |              .py", line 214, in __aenter__                                      
electomate-backend  |                  return await anext(self.gen)                                   
electomate-backend  |                         ^^^^^^^^^^^^^^^^^^^^^                                   
electomate-backend  |                File "/app/src/em_backend/vector/db.py", line 50, in create      
electomate-backend  |                  client = weaviate.connect_to_weaviate_cloud(                   
electomate-backend  |                      cluster_url=settings.wv_url,                               
electomate-backend  |                  ...<3 lines>...                                                
electomate-backend  |                      },                                                         
electomate-backend  |                  )                                                              
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/helpers.p
electomate-backend  |              y", line 107, in connect_to_weaviate_cloud                         
electomate-backend  |                  return __connect(                                              
electomate-backend  |                      WeaviateClient(                                            
electomate-backend  |                  ...<8 lines>...                                                
electomate-backend  |                      )                                                          
electomate-backend  |                  )                                                              
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/helpers.p
electomate-backend  |              y", line 371, in __connect                                         
electomate-backend  |                  raise e                                                        
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/helpers.p
electomate-backend  |              y", line 367, in __connect                                         
electomate-backend  |                  client.connect()                                               
electomate-backend  |                  ~~~~~~~~~~~~~~^^                                               
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/client_executor.p
electomate-backend  |              y", line 149, in connect                                           
electomate-backend  |                  return executor.execute(                                       
electomate-backend  |                         ~~~~~~~~~~~~~~~~^                                       
electomate-backend  |                      response_callback=lambda _: None,                          
electomate-backend  |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                          
electomate-backend  |                      method=self._connection.connect,                           
electomate-backend  |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                           
electomate-backend  |                  )                                                              
electomate-backend  |                  ^                                                              
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/executor.
electomate-backend  |              py", line 99, in execute                                           
electomate-backend  |                  return cast(T, exception_callback(e))                          
electomate-backend  |                                 ~~~~~~~~~~~~~~~~~~^^^                           
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/executor.
electomate-backend  |              py", line 38, in raise_exception                                   
electomate-backend  |                  raise e                                                        
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/executor.
electomate-backend  |              py", line 80, in execute                                           
electomate-backend  |                  call = method(*args, **kwargs)                                 
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py",  
electomate-backend  |              line 958, in connect                                               
electomate-backend  |                  raise e                                                        
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py",  
electomate-backend  |              line 954, in connect                                               
electomate-backend  |                  executor.result(self._ping_grpc("sync"))                       
electomate-backend  |                                  ~~~~~~~~~~~~~~~^^^^^^^^                        
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py",  
electomate-backend  |              line 345, in _ping_grpc                                            
electomate-backend  |                  self.__handle_ping_exception(e)                                
electomate-backend  |                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^                                
electomate-backend  |                File                                                             
electomate-backend  |              "/app/.venv/lib/python3.13/site-packages/weaviate/connect/v4.py",  
electomate-backend  |              line 356, in __handle_ping_exception                               
electomate-backend  |                  raise WeaviateGRPCUnavailableError(                            
electomate-backend  |                      f"v{self.server_version}",                                 
electomate-backend  |              self._connection_params._grpc_address                              
electomate-backend  |                  ) from e                                                       
electomate-backend  |              weaviate.exceptions.WeaviateGRPCUnavailableError:                  
electomate-backend  |              Weaviate v1.32.10 makes use of a high-speed gRPC API as well as a  
electomate-backend  |              REST API.                                                          
electomate-backend  |              Unfortunately, the gRPC health check against Weaviate could not be 
electomate-backend  |              completed.                                                         
electomate-backend  |                                                                                 
electomate-backend  |              This error could be due to one of several reasons:                 
electomate-backend  |              - The gRPC traffic at the specified port is blocked by a firewall. 
electomate-backend  |              - gRPC is not enabled or incorrectly configured on the server or   
electomate-backend  |              the client.                                                        
electomate-backend  |                  - Please check that the server address and port                
electomate-backend  |              (grpc-rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud:443
electomate-backend  |              ) are correct.                                                     
electomate-backend  |              - your connection is unstable or has a high latency. In this case  
electomate-backend  |              you can:                                                           
electomate-backend  |                  - increase init-timeout in                                     
electomate-backend  |              `weaviate.connect_to_local(additional_config=wvc.init.AdditionalCon
electomate-backend  |              fig(timeout=wvc.init.Timeout(init=X)))`                            
electomate-backend  |                  - disable startup checks by connecting using                   
electomate-backend  |              `skip_init_checks=True`
electomate-backend  |      ERROR   Application startup failed. Exiting.
electomate-backend  | <sys>:0: ResourceWarning: unclosed file <_io.TextIOWrapper name=0 mode='r' encoding='UTF-8'>
electomate-backend  | 2025-10-20 10:10:38,695 - INFO - 2 changes detected
electomate-backend  |    WARNING   WatchFiles detected changes in                                     
electomate-backend  |              'src/em_backend/agent/prompts/comparison_party_answer.py'.         
electomate-backend  |              Reloading...
electomate-backend  | 2025-10-20 10:10:38,721 - WARNING - WatchFiles detected changes in 'src/em_backend/agent/prompts/comparison_party_answer.py'. Reloading...
electomate-backend  | 2025-10-20 10:10:41,431 - INFO - 3 changes detected
electomate-backend  |       INFO   Started server process [639]
electomate-backend  | 2025-10-20 10:10:49,675 - INFO - Started server process [639]
electomate-backend  |       INFO   Waiting for application startup.
electomate-backend  | 2025-10-20 10:10:49,678 - INFO - Waiting for application startup.
electomate-backend  | INFO [em_backend.api.routers.v2] Initializing Perplexity client with model='sonar'
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/meta "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://pypi.org/pypi/weaviate-client/json "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/meta "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://pypi.org/pypi/weaviate-client/json "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/.well-known/ready "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/.well-known/ready "HTTP/1.1 200 OK"
electomate-backend  | INFO [uvicorn.error] Application startup complete.
electomate-backend  |       INFO   Application startup complete.
electomate-backend  | 2025-10-20 10:11:38,789 - INFO - 2 changes detected
electomate-backend  |    WARNING   WatchFiles detected changes in 'src/em_backend/agent/agent.py'.    
electomate-backend  |              Reloading...
electomate-backend  | 2025-10-20 10:11:38,824 - WARNING - WatchFiles detected changes in 'src/em_backend/agent/agent.py'. Reloading...
electomate-backend  |       INFO   Shutting down
electomate-backend  | INFO [uvicorn.error] Shutting down
electomate-backend  |       INFO   Waiting for application shutdown.
electomate-backend  | INFO [uvicorn.error] Waiting for application shutdown.
electomate-backend  |       INFO   Application shutdown complete.
electomate-backend  | INFO [uvicorn.error] Application shutdown complete.
electomate-backend  | INFO [uvicorn.error] Finished server process [639]
electomate-backend  |       INFO   Finished server process [639]
electomate-backend  | 2025-10-20 10:11:40,632 - INFO - 3 changes detected
electomate-backend  | 2025-10-20 10:11:43,871 - INFO - 2 changes detected
electomate-backend  |    WARNING   WatchFiles detected changes in 'src/em_backend/agent/agent.py'.    
electomate-backend  |              Reloading...
electomate-backend  | 2025-10-20 10:11:43,883 - WARNING - WatchFiles detected changes in 'src/em_backend/agent/agent.py'. Reloading...
electomate-backend  |       INFO   Started server process [698]
electomate-backend  | 2025-10-20 10:11:55,578 - INFO - Started server process [698]
electomate-backend  |       INFO   Waiting for application startup.
electomate-backend  | 2025-10-20 10:11:55,581 - INFO - Waiting for application startup.
electomate-backend  | INFO [em_backend.api.routers.v2] Initializing Perplexity client with model='sonar'
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/meta "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://pypi.org/pypi/weaviate-client/json "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/meta "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://pypi.org/pypi/weaviate-client/json "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/.well-known/ready "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/.well-known/ready "HTTP/1.1 200 OK"
electomate-backend  |       INFO   Application startup complete.
electomate-backend  | INFO [uvicorn.error] Application startup complete.
electomate-backend  | 2025-10-20 10:12:00,528 - INFO - 3 changes detected
electomate-backend  |       INFO   Started server process [741]
electomate-backend  | 2025-10-20 10:12:10,503 - INFO - Started server process [741]
electomate-backend  |       INFO   Waiting for application startup.
electomate-backend  | 2025-10-20 10:12:10,508 - INFO - Waiting for application startup.
electomate-backend  | INFO [em_backend.api.routers.v2] Initializing Perplexity client with model='sonar'
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/meta "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://pypi.org/pypi/weaviate-client/json "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/meta "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://pypi.org/pypi/weaviate-client/json "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/.well-known/ready "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/.well-known/ready "HTTP/1.1 200 OK"
electomate-backend  |       INFO   Application startup complete.
electomate-backend  | INFO [uvicorn.error] Application startup complete.
electomate-backend  | 2025-10-20 10:12:21,666 - INFO - 2 changes detected
electomate-backend  | 2025-10-20 10:12:27,642 - INFO - 2 changes detected










#####




 new chunking:


 electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing ec61d274-87ab-4d9c-a34e-a0121f28b183 | extra={"X-Request-ID": "daf66322fccb4ae8b6d38cc4a0c9c3a3", "X-Correlation-ID": "56f7650d98bb434d8eb57984154be430", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T11:55:21.571547Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahly "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_parser] Generated chunk 0: 21 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 1: 747 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 2: 85 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 3: 1161 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 4: 288 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 5: 353 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 6: 1137 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 7: 757 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 8: 476 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 9: 725 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 10: 254 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 11: 568 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 12: 439 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 13: 149 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 14: 462 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 15: 194 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 16: 224 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 17: 1091 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 18: 174 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 19: 436 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 20: 303 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 21: 89 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 22: 188 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 23: 217 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 24: 1889 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 25: 205 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 26: 625 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 27: 351 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 28: 289 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 29: 956 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 30: 625 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 31: 419 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 32: 68 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 33: 502 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 34: 371 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 35: 380 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 36: 100 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 37: 702 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 38: 253 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 39: 386 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 40: 468 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 41: 413 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 42: 497 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 43: 218 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 44: 1800 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 45: 251 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 46: 1091 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 47: 710 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 48: 192 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 49: 1044 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 50: 152 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 51: 448 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 52: 701 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 53: 999 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 54: 92 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 55: 581 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 56: 586 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 57: 242 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 58: 461 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 59: 152 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 60: 379 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 61: 149 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 62: 526 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 63: 186 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 64: 543 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 65: 210 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 66: 853 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 67: 636 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 68: 475 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 69: 146 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 70: 279 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 71: 61 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 72: 576 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 73: 167 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 74: 1222 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 75: 195 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 76: 333 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 77: 463 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 78: 1169 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 79: 249 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 80: 92 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 81: 585 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 82: 369 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 83: 462 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 84: 430 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 85: 600 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 86: 511 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 87: 429 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 88: 232 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 89: 128 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 90: 746 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 91: 744 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 92: 231 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 93: 355 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 94: 521 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 95: 405 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 96: 63 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 97: 358 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 98: 567 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 99: 897 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 100: 198 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 101: 836 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 102: 882 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 103: 354 tokens, page unknown
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "ec61d274-87ab-4d9c-a34e-a0121f28b183", "processed_chunks": 104, "X-Request-ID": "daf66322fccb4ae8b6d38cc4a0c9c3a3", "X-Correlation-ID": "56f7650d98bb434d8eb57984154be430", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T11:55:26.447446Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing b52213a9-8298-466a-a376-be3cd519168e | extra={"X-Request-ID": "6a859bbd41b94dbab5775e6918bdac29", "X-Correlation-ID": "5f376f1efb784aaca022a3474db02bfa", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T11:55:26.450532Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking ec61d274-87ab-4d9c-a34e-a0121f28b183 | extra={"X-Request-ID": "daf66322fccb4ae8b6d38cc4a0c9c3a3", "X-Correlation-ID": "56f7650d98bb434d8eb57984154be430", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T11:55:26.451177Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 7225a0b1-b47d-4c7b-932d-e1d9744557f0 | extra={"X-Request-ID": "85a3512ebf4f442c82d75e173708cc3f", "X-Correlation-ID": "3a712013b7f043999d92d96901996e01", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T11:55:26.452499Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished parsing 10afe9af-07ca-4fd1-a9bc-240825ca6ee3 | extra={"X-Request-ID": "12286499d915497ba3984bcb1499af05", "X-Correlation-ID": "3bf20919d6d74dd6972fcc34eb5ad41a", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T11:55:26.453327Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahly "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_parser] Generated chunk 0: 1644 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 1: 1999 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 2: 999 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 3: 527 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 4: 302 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 5: 324 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 6: 303 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 7: 99 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 8: 211 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 9: 179 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 10: 164 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 11: 208 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 12: 453 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 13: 275 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 14: 332 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 15: 1243 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 16: 1643 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 17: 346 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 18: 384 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 19: 1997 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 20: 1905 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 21: 1986 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 22: 126 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 23: 1259 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 24: 1727 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 25: 1940 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 26: 1908 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 27: 779 tokens, page unknown
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "b52213a9-8298-466a-a376-be3cd519168e", "processed_chunks": 28, "X-Request-ID": "6a859bbd41b94dbab5775e6918bdac29", "X-Correlation-ID": "5f376f1efb784aaca022a3474db02bfa", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T11:55:29.797986Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahly "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_parser] Generated chunk 0: 729 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 1: 1673 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 2: 1098 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 3: 1297 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 4: 301 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 5: 711 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 6: 236 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 7: 486 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 8: 547 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 9: 75 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 10: 204 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 11: 184 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 12: 207 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 13: 311 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 14: 159 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 15: 134 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 16: 59 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 17: 40 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 18: 116 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 19: 41 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 20: 440 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 21: 293 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 22: 1082 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 23: 98 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 24: 206 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 25: 397 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 26: 382 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 27: 284 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 28: 150 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 29: 153 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 30: 136 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 31: 297 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 32: 472 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 33: 132 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 34: 111 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 35: 270 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 36: 202 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 37: 278 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 38: 321 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 39: 402 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 40: 286 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 41: 83 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 42: 820 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 43: 523 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 44: 285 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 45: 399 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 46: 232 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 47: 448 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 48: 183 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 49: 201 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 50: 302 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 51: 139 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 52: 181 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 53: 100 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 54: 160 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 55: 211 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 56: 332 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 57: 115 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 58: 118 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 59: 312 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 60: 156 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 61: 131 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 62: 278 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 63: 196 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 64: 215 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 65: 144 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 66: 100 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 67: 260 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 68: 180 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 69: 213 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 70: 183 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 71: 262 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 72: 220 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 73: 175 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 74: 362 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 75: 231 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 76: 230 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 77: 348 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 78: 394 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 79: 294 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 80: 768 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 81: 500 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 82: 295 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 83: 283 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 84: 547 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 85: 330 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 86: 404 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 87: 362 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 88: 403 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 89: 492 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 90: 314 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 91: 550 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 92: 221 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 93: 303 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 94: 1543 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 95: 334 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 96: 764 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 97: 341 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 98: 384 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 99: 863 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 100: 746 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 101: 115 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 102: 147 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 103: 246 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 104: 303 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 105: 115 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 106: 37 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 107: 188 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 108: 339 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 109: 340 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 110: 357 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 111: 444 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 112: 475 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 113: 817 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 114: 755 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 115: 453 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 116: 1157 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 117: 811 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 118: 271 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 119: 352 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 120: 639 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 121: 154 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 122: 707 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 123: 92 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 124: 116 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 125: 110 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 126: 404 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 127: 169 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 128: 149 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 129: 501 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 130: 209 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 131: 296 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 132: 293 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 133: 419 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 134: 135 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 135: 105 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 136: 281 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 137: 14 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 138: 490 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 139: 165 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 140: 401 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 141: 690 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 142: 319 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 143: 154 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 144: 446 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 145: 159 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 146: 168 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 147: 187 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 148: 258 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 149: 87 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 150: 176 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 151: 103 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 152: 367 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 153: 299 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 154: 480 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 155: 712 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 156: 468 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 157: 1143 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 158: 570 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 159: 228 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 160: 721 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 161: 493 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 162: 652 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 163: 625 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 164: 203 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 165: 237 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 166: 182 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 167: 83 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 168: 82 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 169: 133 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 170: 222 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 171: 173 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 172: 43 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 173: 156 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 174: 107 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 175: 217 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 176: 157 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 177: 424 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 178: 389 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 179: 199 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 180: 108 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 181: 303 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 182: 217 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 183: 344 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 184: 270 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 185: 569 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 186: 153 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 187: 158 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 188: 178 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 189: 284 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 190: 141 tokens, page unknown
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "7225a0b1-b47d-4c7b-932d-e1d9744557f0", "processed_chunks": 191, "X-Request-ID": "85a3512ebf4f442c82d75e173708cc3f", "X-Correlation-ID": "3a712013b7f043999d92d96901996e01", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T11:55:36.344574Z"}
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/schema/D2025bundestagswahly "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_parser] Generated chunk 0: 29 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 1: 17 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 2: 905 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 3: 239 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 4: 70 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 5: 230 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 6: 107 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 7: 120 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 8: 67 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 9: 419 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 10: 198 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 11: 325 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 12: 382 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 13: 84 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 14: 220 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 15: 306 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 16: 251 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 17: 355 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 18: 393 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 19: 159 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 20: 695 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 21: 311 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 22: 99 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 23: 452 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 24: 389 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 25: 308 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 26: 272 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 27: 433 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 28: 475 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 29: 865 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 30: 678 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 31: 58 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 32: 1000 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 33: 385 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 34: 203 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 35: 394 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 36: 110 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 37: 313 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 38: 117 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 39: 511 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 40: 395 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 41: 229 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 42: 104 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 43: 112 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 44: 73 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 45: 291 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 46: 314 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 47: 95 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 48: 174 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 49: 370 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 50: 125 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 51: 178 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 52: 89 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 53: 551 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 54: 319 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 55: 283 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 56: 138 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 57: 399 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 58: 165 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 59: 72 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 60: 299 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 61: 181 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 62: 279 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 63: 242 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 64: 52 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 65: 150 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 66: 298 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 67: 72 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 68: 95 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 69: 277 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 70: 156 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 71: 194 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 72: 270 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 73: 115 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 74: 162 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 75: 279 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 76: 279 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 77: 68 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 78: 222 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 79: 109 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 80: 164 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 81: 375 tokens, page unknown
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_parser] Generated chunk 82: 483 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 83: 296 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 84: 124 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 85: 198 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 86: 432 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 87: 355 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 88: 612 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 89: 189 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 90: 356 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 91: 96 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 92: 330 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 93: 576 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 94: 173 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 95: 195 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 96: 179 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 97: 52 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 98: 419 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 99: 191 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 100: 115 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 101: 154 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 102: 193 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 103: 115 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 104: 447 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 105: 241 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 106: 154 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 107: 160 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 108: 301 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 109: 65 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 110: 242 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 111: 265 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 112: 294 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 113: 276 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 114: 275 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 115: 416 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 116: 115 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 117: 156 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 118: 92 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 119: 222 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 120: 149 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 121: 59 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 122: 411 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 123: 176 tokens, page unknown
electomate-backend  | INFO [em_parser] Generated chunk 124: 466 tokens, page unknown
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [httpx] HTTP Request: GET https://rw44gbdgtvq1ux2kpwklta.c0.europe-west3.gcp.weaviate.cloud/v1/nodes "HTTP/1.1 200 OK"
electomate-backend  | INFO [em_backend.vector.db] Chunk upload completed | extra={"document_id": "10afe9af-07ca-4fd1-a9bc-240825ca6ee3", "processed_chunks": 125, "X-Request-ID": "12286499d915497ba3984bcb1499af05", "X-Correlation-ID": "3bf20919d6d74dd6972fcc34eb5ad41a", "span": null, "logger": "em_backend.vector.db", "level": "info", "timestamp": "2025-10-20T11:55:39.946743Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking b52213a9-8298-466a-a376-be3cd519168e | extra={"X-Request-ID": "6a859bbd41b94dbab5775e6918bdac29", "X-Correlation-ID": "5f376f1efb784aaca022a3474db02bfa", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T11:55:39.950968Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 7225a0b1-b47d-4c7b-932d-e1d9744557f0 | extra={"X-Request-ID": "85a3512ebf4f442c82d75e173708cc3f", "X-Correlation-ID": "3a712013b7f043999d92d96901996e01", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T11:55:39.966926Z"}
electomate-backend  | INFO [em_backend.api.routers.documents] Finished chunking 10afe9af-07ca-4fd1-a9bc-240825ca6ee3 | extra={"X-Request-ID": "12286499d915497ba3984bcb1499af05", "X-Correlation-ID": "3bf20919d6d74dd6972fcc34eb5ad41a", "span": null, "logger": "em_backend.api.routers.documents", "level": "info", "timestamp": "2025-10-20T11:55:39.967187Z"}
1   
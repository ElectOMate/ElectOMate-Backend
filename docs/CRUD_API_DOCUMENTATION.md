# FastAPI CRUD Routes for ElectOMate Backend

I have successfully created comprehensive CRUD (Create, Read, Update, Delete) operations for all database models in the ElectOMate Backend. Here's what was implemented:

## Files Created

### 1. Pydantic Schemas (`/src/em_backend/schemas/models.py`)
- **CountryBase/Create/Update/Response/WithElections**: For country operations
- **ElectionBase/Create/Update/Response/WithDetails**: For election operations  
- **PartyBase/Create/Update/Response/WithDetails**: For party operations
- **CandidateBase/Create/Update/Response/WithParty**: For candidate operations
- **DocumentBase/Create/Update/Response/WithParty**: For document operations
- **ProposedQuestionBase/Create/Update/Response/WithParty**: For proposed question operations

All schemas use modern Python type hints (e.g., `str | None` instead of `Optional[str]`) and include proper validation with field length limits.

### 2. CRUD Base Class (`/src/em_backend/crud/base.py`)
Generic CRUD operations supporting:
- `get(id)`: Get single record by UUID
- `get_multi(skip, limit)`: Get multiple records with pagination
- `create(obj_in)`: Create new record
- `update(db_obj, obj_in)`: Update existing record
- `remove(id)`: Delete record by UUID
- `get_with_relationships(id, relationships)`: Get record with related data loaded

### 3. CRUD Instances (`/src/em_backend/crud/__init__.py`)
Pre-configured CRUD instances for all models:
- `country`, `election`, `party`, `candidate`, `document`, `proposed_question`

### 4. API Routers
Created dedicated routers for each model:

#### Countries Router (`/src/em_backend/routers/countries.py`)
- `POST /v2/countries/` - Create country
- `GET /v2/countries/` - List countries (with pagination)
- `GET /v2/countries/{id}` - Get country by ID
- `GET /v2/countries/{id}/with-elections` - Get country with elections
- `PUT /v2/countries/{id}` - Update country
- `DELETE /v2/countries/{id}` - Delete country

#### Elections Router (`/src/em_backend/routers/elections.py`)
- `POST /v2/elections/` - Create election
- `GET /v2/elections/` - List elections (with pagination)
- `GET /v2/elections/{id}` - Get election by ID
- `GET /v2/elections/{id}/with-details` - Get election with country and parties
- `PUT /v2/elections/{id}` - Update election
- `DELETE /v2/elections/{id}` - Delete election

#### Parties Router (`/src/em_backend/routers/parties.py`)
- `POST /v2/parties/` - Create party
- `GET /v2/parties/` - List parties (with pagination)
- `GET /v2/parties/{id}` - Get party by ID
- `GET /v2/parties/{id}/with-details` - Get party with all relationships
- `PUT /v2/parties/{id}` - Update party
- `DELETE /v2/parties/{id}` - Delete party

#### Candidates Router (`/src/em_backend/routers/candidates.py`)
- `POST /v2/candidates/` - Create candidate
- `GET /v2/candidates/` - List candidates (with pagination)
- `GET /v2/candidates/{id}` - Get candidate by ID
- `GET /v2/candidates/{id}/with-party` - Get candidate with party info
- `PUT /v2/candidates/{id}` - Update candidate
- `DELETE /v2/candidates/{id}` - Delete candidate

#### Documents Router (`/src/em_backend/routers/documents.py`)
- `POST /v2/documents/` - Create document
- `GET /v2/documents/` - List documents (with pagination)
- `GET /v2/documents/{id}` - Get document by ID
- `GET /v2/documents/{id}/with-party` - Get document with party info
- `PUT /v2/documents/{id}` - Update document
- `DELETE /v2/documents/{id}` - Delete document

#### Proposed Questions Router (`/src/em_backend/routers/proposed_questions.py`)
- `POST /v2/proposed-questions/` - Create proposed question
- `GET /v2/proposed-questions/` - List proposed questions (with pagination)
- `GET /v2/proposed-questions/{id}` - Get proposed question by ID
- `GET /v2/proposed-questions/{id}/with-party` - Get proposed question with party info
- `PUT /v2/proposed-questions/{id}` - Update proposed question
- `DELETE /v2/proposed-questions/{id}` - Delete proposed question

### 5. Router Registration (`/src/em_backend/routers/v2.py`)
All routers are registered with the v2 router, making them available under the `/v2` prefix.

## Features

### Database Integration
- Uses the existing SQLAlchemy async session dependency from `v2.py`
- Proper transaction management with commit/rollback
- Foreign key relationships preserved

### Error Handling
- HTTP 404 for not found resources
- HTTP 400 for validation and database errors
- Proper exception chaining

### Pagination
- All list endpoints support `skip` and `limit` query parameters
- Default limit of 100 items, maximum of 1000
- Skip parameter for offset-based pagination

### Relationship Loading
- Special endpoints to load related data (e.g., country with elections)
- Uses SQLAlchemy `selectinload` for efficient loading
- Prevents N+1 query problems

### Data Validation
- Pydantic schemas provide request/response validation
- Field length limits prevent database issues
- Type safety with modern Python annotations

## Usage Examples

```python
# Create a country
POST /v2/countries/
{
    "name": "Germany",
    "code": "DE"
}

# Get countries with pagination
GET /v2/countries/?skip=0&limit=10

# Create an election
POST /v2/elections/
{
    "name": "Federal Election 2024",
    "year": 2024,
    "date": "2024-09-22T00:00:00",
    "url": "https://example.com",
    "country_id": "uuid-here"
}

# Get election with all details
GET /v2/elections/{id}/with-details
```

## Database Models Covered
✅ Country
✅ Election  
✅ Party
✅ Candidate
✅ Document
✅ ProposedQuestion

All models have complete CRUD operations with proper validation, error handling, and relationship loading capabilities.
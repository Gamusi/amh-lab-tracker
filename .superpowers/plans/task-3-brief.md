### Task 3: Backend Result Entry API Refactor
**Files:**
- Modify: ackend/app/schemas.py
- Modify: ackend/app/routers/clients.py
- Modify: ackend/app/routers/reports.py (if necessary to match schema changes)

- [ ] **Step 1: Update TestResultCreate Schema**
In ackend/app/schemas.py, modify TestResultCreate.
Remove is_positive from it. The frontend shouldn't send it.

`python
class TestResultCreate(BaseModel):
    order_id: int
    result_value: Optional[str] = None
    parameter_results: Optional[List[ParameterResultItem]] = None
`

- [ ] **Step 2: Update Result Entry Logic (enter_result)**
In ackend/app/routers/clients.py:
When processing eq.result_value or eq.parameter_results, the backend needs to compute is_positive itself using evaluator.py.

Fetch the client's dob and sex from the visit/client records.
Fetch the 	est_name for the order.

For the main result:
`python
from ..evaluator import evaluate_result

# ... fetch dob, sex, test_name ...
eval_dict = evaluate_result(test_name, req.result_value, dob, sex, datetime.date.today())
is_positive = eval_dict.get("is_abnormal", False)

# Also check if it's a manual positive/negative string for tracked tests
if req.result_value and req.result_value.strip().lower() in ["positive", "abnormal", "reactive"]:
    is_positive = True
`
(Apply similarly for parameter results).

- [ ] **Step 3: Add endpoint to add orders to a visit**
In ackend/app/routers/clients.py, add an endpoint to allow adding tests to an existing visit.
POST /api/visits/{visit_id}/orders
Request body should be a list of 	est_ids.

`python
class AddOrdersRequest(BaseModel):
    test_ids: List[int]

@router.post("/api/visits/{visit_id}/orders")
def add_orders_to_visit(visit_id: int, req: AddOrdersRequest, conn: sqlite3.Connection = Depends(get_db)):
    # ... verify visit exists ...
    # ... insert into test_orders for each test_id ...
`

- [ ] **Step 4: Test & Commit**
Verify via tests. Commit changes.

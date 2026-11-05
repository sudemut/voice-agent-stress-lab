from fastapi import APIRouter,HTTPException
from app.repositories.order_repository import OrderRepository
from app.models.order import Order
from fastapi import Depends

router=APIRouter(prefix="/orders")


repository = OrderRepository()
def get_repository():
    return repository

#it is a test 
repository.add(
    Order(
        order_id="ORD-12345",
        customer_email="alice@example.com",
        status="PENDING"
    )
)

@router.get("/{order_id}")
def get_order(order_id:str,repo: OrderRepository = Depends(get_repository)):
    order = repo.get(order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )
    
    return order.to_dict()
@router.post("/{order_id}/cancel")
def cancel_order(order_id:str,repo: OrderRepository = Depends(get_repository)):
    order=repo.get(order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )
    try:
         order.cancel()
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc)
        ) from exc

    return order.to_dict()

@router.get("/{order_id}/status")
def get_order_status(order_id:str,repo: OrderRepository = Depends(get_repository)):
    order=repo.get(order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )
    return {"order_id":order_id, "status": order.status}


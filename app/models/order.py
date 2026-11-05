class Order:
    VALID_ORDER_STATUS={"PENDING","PROCESSING","SHIPPED","DELIVERED","CANCELLED"}
    def __init__(self,order_id,customer_email,status):
        self.order_id=order_id
        self.customer_email=customer_email
        self.status=status

        if not isinstance(customer_email,str) or not customer_email.strip():
            raise ValueError("customer must be a string")
        if not isinstance(order_id,str) or not order_id.strip():
            raise ValueError("order id must be a string")

        if status not in self.VALID_ORDER_STATUS:
            raise ValueError("Order status must be PENDING, PROCESSING ,DELIVERED, SHIPPED or CANCELLED ")

    def can_cancel(self):
        if self.status in ["PENDING","PROCESSING"]:
            return True
        else:
            raise ValueError("Order cannot be cancelled")
    def cancel(self):
        if self.can_cancel():
            self.status="CANCELLED"
        elif not self.can_cancel():
            raise ValueError("Order couldnt cancel")
    

    def to_dict(self):
        return {"order_id":self.order_id, "customer_email": self.customer_email, "status": self.status}
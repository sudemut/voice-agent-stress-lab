class OrderRepository:
    def __init__(self):
        self.orders={}

    def add(self,order):
        if order.order_id in self.orders:
            raise ValueError("There is a already order_id")
        self.orders[order.order_id]=order

    def get(self,order_id):
        return self.orders.get(order_id)

    def list_all(self):
         return list(self.orders.values())
    
    def delete(self,order_id):
        if order_id not in self.orders:
            raise ValueError("There isnt a order")
        del self.orders[order_id]
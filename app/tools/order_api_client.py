import httpx

class OrderAPIClient:
    def __init__(self,base_url):
        self.base_url=base_url.rstrip("/")

    def get_order(self,order_id):
        response = httpx.get(
        f"{self.base_url}/orders/{order_id}",
        timeout=5.0
        )   
        response.raise_for_status()
        data=response.json()
        return data

    def cancel_order(self,order_id):
        response = httpx.post(
        f"{self.base_url}/orders/{order_id}/cancel",
        timeout=5.0
        )   
        response.raise_for_status()
        data=response.json()
        return data
    
    def get_order_status(self,order_id):
        response = httpx.get(
        f"{self.base_url}/orders/{order_id}/status",
        timeout=5.0
        )   
        response.raise_for_status()
        data=response.json()
        return data
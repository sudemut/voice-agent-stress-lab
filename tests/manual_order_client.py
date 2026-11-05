from dotenv import load_dotenv
from app.tools.order_api_client import OrderAPIClient
import os
load_dotenv()

base_url = os.getenv("ORDER_API_BASE_URL")

if not base_url:
    raise ValueError("ORDER_API_BASE_URL is not configured")

order_client = OrderAPIClient(base_url)
print(order_client.get_order("ORD-12345"))
order_client.cancel_order("ORD-12345")
print(order_client.get_order_status("ORD-12345"))
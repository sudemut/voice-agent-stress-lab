class ToolExecutor:
    def __init__(self, order_api_client):
        self.order_api_client=order_api_client

    def execute(self, tool_name, arguments):
        order_id=arguments.get("order_id")
        if not order_id:
            raise ValueError("order_id cannot be empty")
        if tool_name=="get_order":
            return self.order_api_client.get_order(order_id)
        elif tool_name=="cancel_order":
            return self.order_api_client.cancel_order(order_id)
        elif  tool_name=="get_order_status":
            return self.order_api_client.get_order_status(order_id)
        else:
            raise ValueError("We dont have such a tool name")
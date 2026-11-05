
class TaskVerifier:
    def __init__(self, order_api_client):
        self.order_api_client = order_api_client

    def verify(self, runner):
        order_id = runner.scenario.customer_info["order_id"]

        evidence = []
        failure_reasons = []

        successful_calls = [
            call
            for call in runner.tool_call_history
            if call["name"] == "cancel_order"
            and call["arguments"].get("order_id") == order_id
            and call["response"].get("success") is True
            and call["response"].get("result", {}).get("status") == "CANCELLED"
        ]

        if successful_calls:
            evidence.append(
                f"cancel_order executed successfully for {order_id}"
            )
        else:
            failure_reasons.append(
                f"No successful cancellation tool call found for {order_id}"
            )

        try:
            backend_status = self.order_api_client.get_order_status(
                order_id
            )
        except Exception as error:
            failure_reasons.append(
                f"Backend verification unavailable: {error}"
            )
            return "NOT_VERIFIED", evidence, failure_reasons

        if backend_status.get("status") == "CANCELLED":
            evidence.append(
                f"Backend confirms {order_id} is CANCELLED"
            )
        else:
            failure_reasons.append(
                f"Backend status is {backend_status.get('status')}, "
                "expected CANCELLED"
            )
        if (
            successful_calls
            and backend_status.get("status") == "CANCELLED"
        ):
            return "SUCCESS", evidence, failure_reasons

        return "FAILURE", evidence, failure_reasons

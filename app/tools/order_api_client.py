import httpx


class OrderAPIError(Exception):
    """The order backend answered with an HTTP error status (4xx/5xx).

    Raised independently of the HTTP transport, so a real httpx client and
    an in-process FastAPI TestClient produce the same tool error.
    """

    def __init__(self, status_code, detail):
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class OrderAPIClient:
    def __init__(self, base_url, http_client=None):
        self.base_url = base_url.rstrip("/")
        # Any object with httpx-style get/post works: the httpx module,
        # an httpx.Client, or a FastAPI TestClient for an in-process backend.
        self.http_client = http_client if http_client is not None else httpx
        # Injected clients carry their own timeout settings (and TestClient
        # rejects a per-request timeout), so only pass one to plain httpx.
        self.request_options = {"timeout": 5.0} if http_client is None else {}

    def _handle(self, response):
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise OrderAPIError(response.status_code, detail)
        return response.json()

    def get_order(self, order_id):
        response = self.http_client.get(
            f"{self.base_url}/orders/{order_id}",
            **self.request_options
        )
        return self._handle(response)

    def cancel_order(self, order_id):
        response = self.http_client.post(
            f"{self.base_url}/orders/{order_id}/cancel",
            **self.request_options
        )
        return self._handle(response)

    def get_order_status(self, order_id):
        response = self.http_client.get(
            f"{self.base_url}/orders/{order_id}/status",
            **self.request_options
        )
        return self._handle(response)

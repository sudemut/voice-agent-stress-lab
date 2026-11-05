from google.genai import types


cancel_order_declaration = types.FunctionDeclaration(
    name="cancel_order",
    description="Cancel an existing customer order using its order ID.",
    parameters_json_schema={
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The unique ID of the order to cancel."
            }
        },
        "required": ["order_id"]
    }
)

get_order_declaration = types.FunctionDeclaration(
    name="get_order",
    description="Retrieve order information using its unique order ID.",
    parameters_json_schema={
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The unique ID of the order to retrieve."
            }
        },
        "required": ["order_id"]
    }
)


get_order_status_declaration = types.FunctionDeclaration(
    name="get_order_status",
    description="Retrieve the current status of an order using its unique order ID.",
    parameters_json_schema={
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The unique ID of the order id and status to retrieve"
            }
        },
        "required": ["order_id"]
    }
)

order_tools = types.Tool(
    function_declarations=[
        get_order_declaration,
        cancel_order_declaration,
        get_order_status_declaration
    ]
)
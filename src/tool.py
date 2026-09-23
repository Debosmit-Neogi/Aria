KB_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_policy",
        "description": (
            "Retrieve the exact policy text from Northwind Cloud's internal "
            "knowledge base. Call ONLY when the customer explicitly asks for "
            "the policy, rule, or terms. Do NOT call while the customer is "
            "venting, making a general complaint, or in ordinary back-and-forth."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Reformulated search query using internal KB vocabulary.",
                }
            },
            "required": ["query"],
        },
    },
}

def lambda_handler(event, context):
    """
    AWS Lambda handler for the add_numbers tool.

    Expected input:
        {"a": 173, "b": 289}

    Expected output:
        {"result": 462}
    """

    if not isinstance(event, dict):
        raise ValueError("Event must be a JSON object.")

    try:
        a = event["a"]
        b = event["b"]
    except KeyError as exc:
        raise ValueError(f"Missing required parameter: {exc.args[0]}") from exc

    if (
        isinstance(a, bool)
        or isinstance(b, bool)
        or not isinstance(a, int)
        or not isinstance(b, int)
    ):
        raise ValueError("Both a and b must be integers.")

    return {"result": a + b}

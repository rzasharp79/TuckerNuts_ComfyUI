class FloatToString:
    """Converts a FLOAT input to a STRING output with configurable decimal places."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "float_value": ("FLOAT", {"default": 0.0}),
                "decimal_places": ("INT", {"default": 2, "min": 0, "max": 10}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "execute"
    CATEGORY = "TuckerNuts"

    def execute(self, float_value, decimal_places):
        return (f"{float_value:.{decimal_places}f}",)

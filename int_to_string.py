class IntToString:
    """Converts an INT input to a STRING output."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "int_value": ("INT", {"default": 0}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "execute"
    CATEGORY = "TuckerNuts"

    def execute(self, int_value):
        return (str(int_value),)

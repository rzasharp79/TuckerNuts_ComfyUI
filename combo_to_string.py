class ComboToString:
    """Converts a COMBO selection to a STRING output."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "combo_value": ("*",),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "execute"
    CATEGORY = "TuckerNuts"

    def execute(self, combo_value):
        return (str(combo_value),)

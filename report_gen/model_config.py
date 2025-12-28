class ModelConfig:
    def __init__(
        self,
        api_key,
        base_url,
        model,
        pause_seconds,
        system_prompt,
        user_prompt_template,
        response_format,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.pause_seconds = pause_seconds
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.response_format = response_format


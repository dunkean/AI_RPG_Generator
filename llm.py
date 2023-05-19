# import backoff
import traceback
import openai


class LLM():
    def __init__(self, logger, instruction, model_name, api_key=None, api_id=None):
        self.logger = logger
        self.instruction = instruction
        self.model_name = model_name
        self.api_key = api_key
        self.api_id = api_id

    def query(prompt, *, options=None):
        pass


class ChatGPT(LLM):
    def __init__(self, logger, instruction, model_name="gpt-3.5-turbo", api_key=None, api_id=None):
        super().__init__(logger, instruction, model_name, api_key=api_key, api_id=api_id)
        openai.api_key = self.api_key
        openai.organization = self.api_id

    # @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def query(self, prompt, *, options=None):
        temperature = 0.9
        top_p = 1
        frequency_penalty = 0
        presence_penalty = 0.6
        # print("Querying OpenAI: ", options['id'], options['type'])
        content = None
        response = None
        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                messages=[
                    {
                        "role": "system",
                        "content": self.instruction,
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content
            # print(response)
            print(f'{response["usage"]}')
            
        except Exception as e:
            print("OPENAI ERROR ! ", type(e), e)
            traceback.print_exc()

        return content, response

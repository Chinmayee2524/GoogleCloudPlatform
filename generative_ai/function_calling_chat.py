# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START aiplatform_gemini_function_calling_chat]
import vertexai
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerativeModel,
    Part,
    Tool,
)


def generate_function_call_chat(project_id: str, location: str) -> str:
    prompts = []
    summaries = []
    responses = []
    responses_fc = []

    # Initialize Vertex AI
    vertexai.init(project=project_id, location=location)

    # Specify a function declaration and parameters for an API request
    get_product_info_func = FunctionDeclaration(
        name="get_product_sku",
        description="Get the SKU for a product",
        # Function parameters are specified in OpenAPI JSON schema format
        parameters={
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Product name"}
            },
        },
    )

    # Specify another function declaration and parameters for an API request
    get_store_location_func = FunctionDeclaration(
        name="get_store_location",
        description="Get the location of the closest store",
        parameters={
            "type": "object",
            "properties": {"location": {"type": "string", "description": "Location"}},
        },
    )

    retail_tool = Tool(
        function_declarations=[
            get_product_info_func,
            get_store_location_func,
        ],
    )

    # Initialize Gemini model
    model = GenerativeModel(
        "gemini-1.0-pro", generation_config={"temperature": 0}, tools=[retail_tool]
    )

    # Start a chat session
    chat = model.start_chat()

    # Send a prompt for the first conversation turn that should invoke the get_product_sku function
    prompt = "Do you have the Pixel 8 Pro in stock?"
    response_fc = chat.send_message(prompt)
    prompts.append(prompt)
    responses_fc.append(response_fc)

    # Here you would make an API request to an external system to retrieve the product SKU.
    # We'll use mock data to simulate an external API response.
    api_response = {"sku": "GA04834-US", "in_stock": "yes"}

    # Return the API response to Gemini so it can generate a model response or request another function call
    response = chat.send_message(
        Part.from_function_response(
            name="get_product_sku",
            response={
                "content": api_response,
            },
        ),
    )
    responses.append(response)

    # Extract the text from the summary response
    summary = response.candidates[0].content.parts[0].text
    summaries.append(summary)

    # Send a prompt for the second conversation turn that should invoke the get_store_location function
    prompt = "Is there a store in Mountain View, CA that I can visit to try it out?"
    response_fc = chat.send_message(prompt)
    prompts.append(prompt)
    responses_fc.append(response_fc)

    # Here you would make an API request to retrieve the store location closest to the user.
    # We'll use mock data to simulate an external API response.
    api_response = {"store": "2000 N Shoreline Blvd, Mountain View, CA 94043, US"}

    # Return the API response to Gemini so it can generate a model response or request another function call
    response = chat.send_message(
        Part.from_function_response(
            name="get_store_location",
            response={
                "content": api_response,
            },
        ),
    )
    responses.append(response)

    # Extract the text from the summary response
    summary = response.candidates[0].content.parts[0].text
    summaries.append(summary)

    return prompts, summaries, responses, responses_fc


# [END aiplatform_gemini_function_calling_chat]
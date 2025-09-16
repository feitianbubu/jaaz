from typing import Annotated, Dict, Any
from pydantic import BaseModel, Field, create_model
from langchain_core.tools import tool, InjectedToolCallId  # type: ignore
from langchain_core.runnables import RunnableConfig
from tools.utils.image_generation_core import generate_image_with_provider
from services.config_service import config_service


class DynamicImageInputSchema(BaseModel):
    prompt: str = Field(
        description="Required. The prompt for image generation. Describe what you want to see in the image."
    )
    tool_call_id: Annotated[str, InjectedToolCallId]


def create_image_tool_config(model_name: str, display_name: str, description: str,
                           default_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create dynamic image tool configuration"""
    default_params = default_params or {}

    # Base schema fields
    schema_fields = {
        'prompt': (str, Field(description="Required. The prompt for image generation. Describe what you want to see in the image." if not default_params.get('prompt') else default_params.get('prompt'))),
        'tool_call_id': (str, InjectedToolCallId)
    }

    # Add common optional fields
    schema_fields.update({
        'aspect_ratio': (str, Field(default=default_params.get('aspect_ratio', "1:1"), description="Optional. Aspect ratio of the image, only these values are allowed: 1:1, 16:9, 4:3, 3:4, 9:16. Choose the best fitting aspect ratio according to the prompt.")),
        'input_images': (list[str] | None, Field(default=None, description="Optional. Images to use as reference or for editing. Pass a list of image_id here, e.g. ['im_jurheut7.png']."))
    })

    # Add any additional custom fields from config
    for param_name, param_config in default_params.items():
        if param_name in ['prompt', 'aspect_ratio', 'input_images']:
            continue  # Already handled above
        if isinstance(param_config, dict) and 'type' in param_config:
            # Handle custom parameter configs
            field_type = {
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list[str]
            }.get(param_config['type'], str)

            schema_fields[param_name] = (
                field_type,
                Field(
                    default=param_config.get('default'),
                    description=param_config.get('description', f"Optional. {param_name} parameter.")
                )
            )

    # Create dynamic schema
    DynamicSchema = create_model(
        f'GenerateImageBy{model_name.replace("-", "_").replace(".", "_")}InputSchema',
        **schema_fields
    )

    return {
        'model_name': model_name,
        'display_name': display_name,
        'description': description,
        'schema': DynamicSchema,
        'default_params': default_params
    }


def create_dynamic_image_tool(tool_config: Dict[str, Any]):
    """Create a dynamic image generation tool based on configuration"""
    model_name = tool_config['model_name']
    display_name = tool_config['display_name']
    description = tool_config['description']
    SchemaClass = tool_config['schema']
    default_params = tool_config.get('default_params', {})

    tool_name = f"generate_image_by_{model_name.replace('-', '_').replace('.', '_')}_jaaz"
    tool_config['tool_name'] = tool_name

    @tool(tool_name,
          description=description,
          args_schema=SchemaClass)
    async def dynamic_image_tool(
        prompt: str,
        config: RunnableConfig,
        input_images: list[str] | None = None,
        aspect_ratio: str = None,
        **kwargs
    ) -> str:
        """
        Generate an image using {display_name} model via Jaaz service
        """
        ctx = config.get('configurable', {})
        canvas_id = ctx.get('canvas_id', '')
        session_id = ctx.get('session_id', '')
        print(f'🛠️ canvas_id {canvas_id} session_id {session_id}')

        # Get tool_call_id from kwargs or context
        tool_call_id = kwargs.get('tool_call_id', '') or ctx.get('tool_call_id', '')
        print(f'🛠️ {display_name} Image Generation tool_call_id: {tool_call_id}')

        # Inject the tool call id into the context
        ctx['tool_call_id'] = tool_call_id

        try:
            # Use aspect_ratio from kwargs if provided, otherwise use default
            effective_aspect_ratio = aspect_ratio or default_params.get('aspect_ratio', '1:1')

            # Get token from context
            token = ctx.get('token', None)

            # Generate image using the core function
            return await generate_image_with_provider(
                canvas_id=canvas_id,
                session_id=session_id,
                provider='jaaz',
                model=model_name,
                prompt=prompt,
                aspect_ratio=effective_aspect_ratio,
                input_images=input_images,
                token=token,
            )

        except Exception as e:
            print(f"Error in {display_name} image generation: {e}")
            raise e

    return dynamic_image_tool


def get_image_model_configs() -> Dict[str, Dict[str, Any]]:
    """Get all image model configurations from app config"""
    image_configs = {}

    # Get jaaz provider config
    jaaz_config = config_service.app_config.get('jaaz', {})

    # Look for image models in config
    if 'models' in jaaz_config:
        for model_name, model_config in jaaz_config['models'].items():
            if model_config.get('type') == 'image':
                display_name = model_config.get('display_name', model_name)
                description = model_config.get('description', f"Generate images using {display_name}")

                image_configs[model_name] = create_image_tool_config(
                    model_name=model_name,
                    display_name=display_name,
                    description=description,
                    default_params=model_config.get('default_params', {})
                )

    # Add default image models if not in config
    default_models = {
    }

    # Add missing models
    for model_name, model_info in default_models.items():
        if model_name not in image_configs:
            image_configs[model_name] = create_image_tool_config(
                model_name=model_name,
                display_name=model_info['display_name'],
                description=model_info['description']
            )

    return image_configs


# Create dynamic tools
IMAGE_MODEL_CONFIGS = get_image_model_configs()
DYNAMIC_IMAGE_TOOLS = {}

for model_name, tool_config in IMAGE_MODEL_CONFIGS.items():
    tool_func = create_dynamic_image_tool(tool_config)
    tool_name = tool_config['tool_name']
    DYNAMIC_IMAGE_TOOLS[tool_name] = {
        'tool_function': tool_func,
        'model_name': model_name,
        'display_name': tool_config['display_name'],
        'type': 'image',
        'provider': 'jaaz'
    }
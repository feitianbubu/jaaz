from typing import Annotated, Dict, Any
from pydantic import BaseModel, Field, create_model
from langchain_core.tools import tool, InjectedToolCallId  # type: ignore
from langchain_core.runnables import RunnableConfig
from services.jaaz_service import JaazService
from tools.video_generation.video_canvas_utils import send_video_start_notification, process_video_result
from .utils.image_utils import process_input_image
from services.config_service import config_service


class DynamicVideoInputSchema(BaseModel):
    prompt: str = Field(
        description="Required. The prompt for video generation. Describe what you want to see in the video."
    )
    input_images: list[str] = Field(
        description="Required. Images to use as reference or starting frame. Pass a list of image_id here, e.g. ['im_jurheut7.png']. Only the first image will be used as start_image."
    )
    tool_call_id: Annotated[str, InjectedToolCallId]


def create_video_tool_config(model_name: str, display_name: str, description: str,
                           default_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create dynamic video tool configuration"""
    default_params = default_params or {}
    
    # Base schema fields
    schema_fields = {
        'prompt': (str, Field(description="Required. The prompt for video generation. Describe what you want to see in the video.")),
        'input_images': (list[str], Field(description="Required. Images to use as reference or starting frame. Pass a list of image_id here, e.g. ['im_jurheut7.png']. Only the first image will be used as start_image.")),
        'tool_call_id': (str, InjectedToolCallId)
    }

    schema_fields.update({
        'negative_prompt': (str, Field(default="", description="Optional. Negative prompt to specify what you don't want in the video.")),
        'guidance_scale': (float, Field(default=0.5, description="Optional. Guidance scale for generation (0.0 to 1.0). Higher values follow the prompt more closely.")),
        'aspect_ratio': (str, Field(default="16:9", description="Optional. The aspect ratio of the video. Allowed values: 1:1, 16:9, 4:3, 21:9")),
        'duration': (int, Field(default=5, description="Optional. The duration of the video in seconds. Use 5 by default. Allowed values: 5, 10."))
    })
    
    # Create dynamic schema
    DynamicSchema = create_model(
        f'GenerateVideoBy{model_name.replace("-", "_").replace(".", "_")}InputSchema',
        **schema_fields
    )
    
    return {
        'model_name': model_name,
        'display_name': display_name,
        'description': description,
        'schema': DynamicSchema,
        'default_params': default_params
    }


def create_dynamic_video_tool(tool_config: Dict[str, Any]):
    """Create a dynamic video generation tool based on configuration"""
    model_name = tool_config['model_name']
    display_name = tool_config['display_name']
    description = tool_config['description']
    SchemaClass = tool_config['schema']
    default_params = tool_config.get('default_params', {})
    
    tool_name = f"generate_video_by_{model_name.replace('-', '_').replace('.', '_')}_jaaz"
    tool_config['tool_name'] = tool_name
    
    @tool(tool_name,
          description=description,
          args_schema=SchemaClass)
    async def dynamic_video_tool(
        prompt: str,
        input_images: list[str],
        config: RunnableConfig,
        negative_prompt: str = "",
        guidance_scale: float = 0.5,
        aspect_ratio: str = "16:9",
        duration: int = 5,
        **kwargs
    ) -> str:
        """
        Generate a video using {display_name} model via Jaaz service
        """
        ctx = config.get('configurable', {})
        canvas_id = ctx.get('canvas_id', '')
        session_id = ctx.get('session_id', '')
        print(f'🛠️ canvas_id {canvas_id} session_id {session_id}')

        # Get tool_call_id from kwargs or context
        tool_call_id = kwargs.get('tool_call_id', '') or ctx.get('tool_call_id', '')
        print(f'🛠️ {display_name} Video Generation tool_call_id: {tool_call_id}')

        # Inject the tool call id into the context
        ctx['tool_call_id'] = tool_call_id

        try:
            # Validate input_images is provided and not empty
            if not input_images or len(input_images) == 0:
                raise ValueError(
                    "input_images is required and cannot be empty. Please provide at least one image.")

            # Send start notification
            await send_video_start_notification(
                session_id,
                f"Starting {display_name} video generation..."
            )

            # Process input images (use first image as start_image)
            # first_image = input_images[0]
            # processed_image = await process_input_image(first_image)
            # if not processed_image:
            #     raise ValueError(
            #         f"Failed to process input image: {first_image}. Please check if the image exists and is valid.")
            #
            # # Extract pure base64 data from data URL format
            # if processed_image.startswith('data:'):
            #     processed_image = processed_image.split(',')[1]
            #
            # Create Jaaz service and generate video with token from context
            token = ctx.get('token', '')
            jaaz_service = JaazService(token=token)
            
            # Build generation parameters
            generation_params = {
                'prompt': prompt,
                'model': model_name,
                'input_images': input_images
            }

            generation_params.update({
                'negative_prompt': negative_prompt,
                'guidance_scale': guidance_scale,
                'aspect_ratio': aspect_ratio,
                'duration': duration
            })
            
            result = await jaaz_service.generate_video(**generation_params)

            video_url = result.get('result_url')
            if not video_url:
                raise Exception("No video URL returned from generation")

            # Process video result (save, update canvas, notify)
            return await process_video_result(
                video_url=video_url,
                session_id=session_id,
                canvas_id=canvas_id,
                provider_name=f"jaaz_{model_name.replace('-', '_').replace('.', '_')}",
            )

        except Exception as e:
            print(f"Error in {display_name} video generation: {e}")
            raise e

    return dynamic_video_tool


def get_video_model_configs() -> Dict[str, Dict[str, Any]]:
    """Get all video model configurations from app config"""
    video_configs = {}
    
    # Get jaaz provider config
    jaaz_config = config_service.app_config.get('jaaz', {})
    
    # Look for video models in config
    if 'models' in jaaz_config:
        for model_name, model_config in jaaz_config['models'].items():
            if model_config.get('type') == 'video':
                display_name = model_config.get('display_name', model_name)
                description = model_config.get('description', f"Generate videos using {display_name}")
                
                video_configs[model_name] = create_video_tool_config(
                    model_name=model_name,
                    display_name=display_name,
                    description=description,
                    default_params=model_config.get('default_params', {})
                )
    
    # Add default video models if not in config
    default_models = {
    }
    
    # Add missing models
    for model_name, model_info in default_models.items():
        if model_name not in video_configs:
            video_configs[model_name] = create_video_tool_config(
                model_name=model_name,
                display_name=model_info['display_name'],
                description=model_info['description']
            )
    
    return video_configs


# Create dynamic tools
VIDEO_MODEL_CONFIGS = get_video_model_configs()
DYNAMIC_VIDEO_TOOLS = {}

for model_name, tool_config in VIDEO_MODEL_CONFIGS.items():
    tool_func = create_dynamic_video_tool(tool_config)
    tool_name = tool_config['tool_name']  # Add this line to define tool_name
    DYNAMIC_VIDEO_TOOLS[tool_name] = {
        'tool_function': tool_func,
        'model_name': model_name,
        'display_name': tool_config['display_name'], 
        'type': 'video',
        'provider': 'jaaz'
    }
import os
import uuid
from typing import List
from urllib.parse import urljoin
from fastapi import APIRouter, BackgroundTasks, Path
from fastapi import Depends, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import constr

from kairon.shared.auth import Authentication
from kairon.api.models import (
    TextData,
    ListData,
    Response,
    Endpoint,
    RasaConfig,
    HttpActionConfigRequest, BulkTrainingDataAddRequest, TrainingDataGeneratorStatusModel, StoryRequest,
    SynonymRequest, RegexRequest,
    StoryType, ComponentConfig, SlotRequest, DictData, LookupTablesRequest, Forms, SlotSetActionRequest,
    TextDataLowerCase
)
from kairon.shared.models import User
from kairon.shared.data.constant import EVENT_STATUS, ENDPOINT_TYPE
from kairon.shared.data.data_objects import TrainingExamples
from kairon.shared.data.model_processor import ModelProcessor
from kairon.shared.data.processor import MongoProcessor
from kairon.shared.data.training_data_generation_processor import TrainingDataGenerationProcessor
from kairon.events.events import EventsTrigger
from kairon.exceptions import AppException
from kairon.shared.importer.processor import DataImporterLogProcessor
from kairon.shared.actions.data_objects import ActionServerLogs
from kairon.shared.utils import Utility
from kairon.shared.data.utils import DataUtility
from kairon.shared.test.processor import ModelTestingLogProcessor

router = APIRouter()
mongo_processor = MongoProcessor()


@router.get("/intents", response_model=Response)
async def get_intents(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches list of existing intents for particular bot
    """
    return Response(data=mongo_processor.get_intents(current_user.get_bot())).dict()


@router.get("/intents/all", response_model=Response)
async def get_intents_with_training_examples(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches list of existing intents and associated training examples for particular bot
    """
    return Response(data=mongo_processor.get_intents_and_training_examples(current_user.get_bot())).dict()


@router.post("/intents", response_model=Response)
async def add_intents(
        request_data: TextDataLowerCase, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Adds a new intent to the bot
    """
    intent_id = mongo_processor.add_intent(
        text=request_data.data,
        bot=current_user.get_bot(),
        user=current_user.get_user(),
        is_integration=current_user.get_integration_status()
    )
    return {"message": "Intent added successfully!", "data": {"_id": intent_id}}


@router.delete("/intents/{intent}/{delete_dependencies}", response_model=Response)
async def delete_intent(
        intent: str = Path(default=None, description="intent name", example="greet"),
        delete_dependencies: bool = Path(
            default=True,
            description="""if True delete bot data related to this intent otherwise only delete intent""",
        ),
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    deletes an intent including training examples and stories
    """
    mongo_processor.delete_intent(
        intent, current_user.get_bot(), current_user.get_user(), current_user.get_integration_status(),
        delete_dependencies
    )
    return {"message": "Intent deleted!"}


@router.post("/intents/search", response_model=Response)
async def search_training_examples(
        request_data: TextData, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Searches existing training examples
    """
    search_items = list(
        mongo_processor.search_training_examples(
            request_data.data, current_user.get_bot()
        )
    )
    return {"data": {"searched_items": search_items}}


@router.get("/training_examples/{intent}", response_model=Response)
async def get_training_examples(
        intent: str, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches all training examples against intent
    """
    return {
        "data": list(
            mongo_processor.get_training_examples(intent, current_user.get_bot())
        )
    }


@router.get("/training_examples", response_model=Response)
async def get_all_training_examples_for_bot(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches all training examples against a bot.
    """
    return {
        "data": mongo_processor.get_training_examples_as_dict(current_user.get_bot())
    }


@router.post("/training_examples/{intent}", response_model=Response)
async def add_training_examples(
        intent: constr(to_lower=True, strip_whitespace=True),
        request_data: ListData,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Adds training example in particular intent
    """
    results = list(
        mongo_processor.add_training_example(
            request_data.data, intent, current_user.get_bot(), current_user.get_user(),
            current_user.get_integration_status()
        )
    )
    return {"data": results}


@router.post("/training_examples/move/{intent}", response_model=Response)
async def move_training_examples(
        intent: constr(to_lower=True, strip_whitespace=True),
        request_data: ListData,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Moves training example to particular intent
    """
    results = list(
        mongo_processor.add_or_move_training_example(
            request_data.data, intent, current_user.get_bot(), current_user.get_user()
        )
    )
    return {"data": results}


@router.put("/training_examples/{intent}/{id}", response_model=Response)
async def edit_training_examples(
        intent: str,
        id: str,
        request_data: TextData,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Updates existing training example
    """
    mongo_processor.edit_training_example(
        id, request_data.data, intent, current_user.get_bot(), current_user.get_user()
    )
    return {"message": "Training Example updated!"}


@router.delete("/training_examples", response_model=Response)
async def remove_training_examples(
        request_data: TextData, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Deletes existing training example
    """
    mongo_processor.remove_document(
        TrainingExamples,
        request_data.data,
        current_user.get_bot(),
        current_user.get_user(),
    )
    return {"message": "Training Example removed!"}


@router.get("/response/all", response_model=Response)
async def get_all_responses(
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches list of all utterances added.
    """
    return {
        "data": list(mongo_processor.get_all_responses(current_user.get_bot()))
    }


@router.get("/response/{utterance}", response_model=Response)
async def get_responses(
        utterance: str, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches list of utterances against utterance name
    """
    return {
        "data": list(mongo_processor.get_response(utterance, current_user.get_bot()))
    }


@router.post("/response/{utterance}", response_model=Response)
async def add_responses(
        request_data: TextData,
        utterance: constr(to_lower=True, strip_whitespace=True),
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Adds utterance value in particular utterance
    """
    utterance_id = mongo_processor.add_text_response(
        request_data.data, utterance, current_user.get_bot(), current_user.get_user()
    )
    return {"message": "Response added!", "data": {"_id": utterance_id}}


@router.put("/response/{utterance}/{id}", response_model=Response)
async def edit_responses(
        utterance: str,
        id: str,
        request_data: TextData,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Updates existing utterance value
    """
    mongo_processor.edit_text_response(
        id,
        request_data.data,
        utterance,
        current_user.get_bot(),
        current_user.get_user(),
    )
    return {
        "message": "Utterance updated!",
    }


@router.delete("/response/{delete_utterance}", response_model=Response)
async def remove_responses(
        request_data: TextData,
        delete_utterance: bool = Path(default=False, description="Deletes utterance if True"),
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Deletes existing utterance completely along with its examples.
    """
    if delete_utterance:
        mongo_processor.delete_utterance(
            request_data.data, current_user.get_bot(), current_user.get_user()
        )
    else:
        mongo_processor.delete_response(
            request_data.data, current_user.get_bot(), current_user.get_user()
        )
    return {
        "message": "Utterance removed!",
    }


@router.post("/stories", response_model=Response)
async def add_story(
        story: StoryRequest, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Adds a story (conversational flow) in the particular bot
    """
    return {
        "message": "Flow added successfully",
        "data": {
            "_id": mongo_processor.add_complex_story(
                story.dict(),
                current_user.get_bot(),
                current_user.get_user(),
            )
        },
    }


@router.put("/stories", response_model=Response)
async def update_story(
        story: StoryRequest, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Updates a story (conversational flow) in the particular bot
    """
    return {
        "message": "Flow updated successfully",
        "data": {
            "_id": mongo_processor.update_complex_story(
                story.dict(),
                current_user.get_bot(),
                current_user.get_user(),
            )
        },
    }


@router.get("/stories", response_model=Response)
async def get_stories(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches existing list of stories (conversation flows)
    """
    return {"data": list(mongo_processor.get_stories(current_user.get_bot()))}


@router.delete("/stories/{story}/{type}", response_model=Response)
async def delete_stories(story: str = Path(default=None, description="Story name", example="happy_path"),
                         type: str = StoryType,
                         current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Updates a story (conversational flow) in the particular bot
    """
    mongo_processor.delete_complex_story(
        story,
        type,
        current_user.get_bot(),
        current_user.get_user(),
    )
    return {
        "message": "Flow deleted successfully"
    }


@router.get("/utterance_from_intent/{intent}", response_model=Response)
async def get_story_from_intent(
        intent: str, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches the utterance or response that is mapped to a particular intent
    """
    response = mongo_processor.get_utterance_from_intent(intent, current_user.get_bot())
    return_data = {"name": response[0], "type": response[1]}
    return {"data": return_data}


@router.post("/chat", response_model=Response)
async def chat(
        request_data: TextData,
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches a bot response for a given text/query.
    It is basically used to test the chat functionality of the agent
    """
    return await Utility.chat(request_data.data,
                              bot=current_user.get_bot(),
                              user=current_user.get_user(),
                              email=current_user.email)


@router.post("/chat/{user}", response_model=Response)
async def augment_chat(
        request_data: TextData,
        user: str = Path(default="default", description="user for which the chats needs to be log"),
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches a bot response for a given text/query for user on path parameter.
    It is basically used to test the chat functionality of the agent
    """
    return await Utility.chat(request_data.data,
                              bot=current_user.get_bot(),
                              user=user,
                              email=current_user.email)


@router.post("/train", response_model=Response)
async def train(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Trains the chatbot
    """
    DataUtility.train_model(background_tasks, current_user.get_bot(), current_user.get_user(), current_user.email, 'train')
    return {"message": "Model training started."}


@router.get("/model/reload", response_model=Response)
async def reload_model(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Reloads model with configuration in cache
    """
    response = Utility.reload_model(
        bot=current_user.get_bot(),
        email=current_user.email)
    return response


@router.get("/train/history", response_model=Response)
async def get_model_training_history(
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Fetches model training history, when and who trained the bot
    """
    training_history = list(ModelProcessor.get_training_history(current_user.get_bot()))
    return {"data": {"training_history": training_history}}


@router.post("/deploy", response_model=Response)
async def deploy(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Deploys the latest bot model to the particular http endpoint
    """
    response = mongo_processor.deploy_model(
        bot=current_user.get_bot(), user=current_user.get_user()
    )
    return {"message": response}


@router.get("/deploy/history", response_model=Response)
async def deployment_history(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches model deployment history, when and who deployed the model
    """
    return {
        "data": {
            "deployment_history": list(
                mongo_processor.get_model_deployment_history(bot=current_user.get_bot())
            )
        }
    }


@router.post("/upload", response_model=Response)
async def upload_files(
        background_tasks: BackgroundTasks,
        training_files: List[UploadFile] = File(...),
        import_data: bool = True,
        overwrite: bool = True,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Uploads training data nlu.md, domain.yml, stories.md, config.yml, rules.yml and http_action.yml files.
    """
    is_event_data = await mongo_processor.validate_and_log(current_user.get_bot(), current_user.get_user(),
                                                           training_files, overwrite)
    if is_event_data:
        background_tasks.add_task(EventsTrigger.trigger_data_importer, current_user.get_bot(), current_user.get_user(),
                                  import_data, overwrite)
    return {"message": "Upload in progress! Check logs."}


@router.post("/upload/data_generation/file", response_model=Response)
async def upload_data_generation_file(
    background_tasks: BackgroundTasks,
    doc: UploadFile = File(...),
    current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Uploads document for training data generation and triggers event for intent creation
    """
    TrainingDataGenerationProcessor.is_in_progress(current_user.get_bot())
    TrainingDataGenerationProcessor.check_data_generation_limit(current_user.get_bot())
    file_path = await Utility.upload_document(doc)
    TrainingDataGenerationProcessor.set_status(bot=current_user.get_bot(),
                                               user=current_user.get_user(), status=EVENT_STATUS.INITIATED.value,
                                               document_path=file_path)
    token = Authentication.create_access_token(data={"sub": current_user.email})
    background_tasks.add_task(
        DataUtility.trigger_data_generation_event, current_user.get_bot(), current_user.get_user(), token
    )
    return {"message": "File uploaded successfully and training data generation has begun"}


@router.get("/download/data")
async def download_data(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Downloads training data nlu.md, domain.yml, stories.md, config.yml files
    """
    file = mongo_processor.download_files(current_user.get_bot())
    response = FileResponse(
        file, filename=os.path.basename(file), background=background_tasks
    )
    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=" + os.path.basename(file)
    return response


@router.get("/download/model")
async def download_model(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Downloads latest trained model file
    """
    try:
        model_path = Utility.get_latest_model(current_user.get_bot())
        response = FileResponse(
            model_path,
            filename=os.path.basename(model_path),
            background=background_tasks,
        )
        response.headers[
            "Content-Disposition"
        ] = "attachment; filename=" + os.path.basename(model_path)
        return response
    except Exception as e:
        raise AppException(str(e))


@router.post("/test", response_model=Response)
async def test_model(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Run tests on a trained model.
    """
    Utility.is_model_file_exists(current_user.get_bot())
    ModelTestingLogProcessor.is_event_in_progress(current_user.get_bot())
    ModelTestingLogProcessor.is_limit_exceeded(current_user.get_bot())
    background_tasks.add_task(EventsTrigger.trigger_model_testing, current_user.get_bot(), current_user.get_user())
    return {"message": "Testing in progress! Check logs."}


@router.get("/endpoint", response_model=Response)
async def get_endpoint(current_user: User = Depends(Authentication.get_current_user_and_bot),):
    """
    Fetches the http and mongo endpoint for the bot
    """
    endpoint = mongo_processor.get_endpoints(
        current_user.get_bot(), mask_characters=True, raise_exception=False
    )
    return {"data": {"endpoint": endpoint}}


@router.put("/endpoint", response_model=Response)
async def set_endpoint(
        background_tasks: BackgroundTasks,
        endpoint: Endpoint,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Saves or Updates the bot endpoint configuration
    """
    mongo_processor.add_endpoints(
        endpoint.dict(), current_user.get_bot(), current_user.get_user()
    )

    if endpoint.action_endpoint:
        background_tasks.add_task(Utility.reload_model, current_user.get_bot(), current_user.email)
    return {"message": "Endpoint saved successfully!"}


@router.delete("/endpoint/{endpoint_type}", response_model=Response)
async def delete_endpoint(
        endpoint_type: ENDPOINT_TYPE = Path(default=None, description="One of bot_endpoint, action_endpoint, "
                                                                      "history_endpoint", example="bot_endpoint"),
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Deletes the bot endpoint configuration
    """
    mongo_processor.delete_endpoint(
        current_user.get_bot(), endpoint_type
    )

    return {"message": "Endpoint removed"}


@router.get("/config", response_model=Response)
async def get_config(current_user: User = Depends(Authentication.get_current_user_and_bot), ):
    """
    Fetches bot pipeline and polcies configurations
    """
    config = mongo_processor.load_config(current_user.get_bot())
    return {"data": {"config": config}}


@router.put("/config", response_model=Response)
async def set_config(
        config: RasaConfig, current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Saves or Updates the bot pipeline and policies configurations
    """
    mongo_processor.save_config(
        config.dict(), current_user.get_bot(), current_user.get_user()
    )
    return {"message": "Config saved!"}


@router.put("/config/properties", response_model=Response)
async def set_epoch_and_fallback_properties(config: ComponentConfig, current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Set properties (epoch and fallback) in the bot pipeline and policies configurations
    """
    mongo_processor.save_component_properties(config.dict(), current_user.get_bot(), current_user.get_user())
    return {"message": "Config saved"}


@router.get("/config/properties", response_model=Response)
async def list_epoch_and_fallback_properties(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    List properties (epoch and fallback) in the bot pipeline and policies configurations
    """
    config = mongo_processor.list_epoch_and_fallback_config(current_user.get_bot())
    return {"data": config}


@router.get("/templates/use-case", response_model=Response)
async def get_templates(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches use-case templates name
    """
    return {"data": {"use-cases": Utility.list_directories("./template/use-cases")}}


@router.post("/templates/use-case", response_model=Response)
async def set_templates(
        request_data: TextData, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Applies the use-case template
    """
    await mongo_processor.apply_template(
        request_data.data, bot=current_user.get_bot(), user=current_user.get_user()
    )
    return {"message": "Data applied!"}


@router.get("/templates/config", response_model=Response)
async def get_config_template(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches config templates
    """
    return {"data": {"config-templates": mongo_processor.get_config_templates()}}


@router.post("/templates/config", response_model=Response)
async def set_config_template(
        request_data: TextData, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Applies the config template
    """
    mongo_processor.apply_config(
        request_data.data, current_user.get_bot(), current_user.get_user()
    )
    return {"message": "Config applied!"}


@router.post("/action/httpaction", response_model=Response)
async def add_http_action(request_data: HttpActionConfigRequest, current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Stores the http action config and story event
    """
    http_config_id = mongo_processor.add_http_action_config(request_data.dict(), current_user.get_user(),
                                                            current_user.get_bot())
    response = {"http_config_id": http_config_id}
    message = "Http action added!"
    return Response(data=response, message=message)


@router.get("/action/httpaction/{action}", response_model=Response)
async def get_http_action(action: str = Path(default=None, description="action name", example="http_action"),
                          current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Returns configuration set for the HTTP action
    """
    http_action_config = mongo_processor.get_http_action_config(action_name=action,
                                                                           bot=current_user.get_bot())
    action_config = DataUtility.build_http_response_object(http_action_config, current_user.get_user(), current_user.get_bot())
    return Response(data=action_config)


@router.get("/action/httpaction", response_model=Response)
async def list_http_actions(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Returns list of http actions for bot.
    """
    actions = mongo_processor.list_http_actions(bot=current_user.get_bot())
    return Response(data=actions)


@router.get("/actions", response_model=Response)
async def list_actions(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Returns list of actions for bot.
    """
    actions = mongo_processor.list_actions(bot=current_user.get_bot())
    return Response(data=actions)


@router.put("/action/httpaction", response_model=Response)
async def update_http_action(request_data: HttpActionConfigRequest,
                             current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Updates the http action config and related story event
    """
    http_config_id = mongo_processor.update_http_config(request_data=request_data, user=current_user.get_user(),
                                                        bot=current_user.get_bot())
    response = {"http_config_id": http_config_id}
    message = "Http action updated!"
    return Response(data=response, message=message)


@router.delete("/action/httpaction/{action}", response_model=Response)
async def delete_http_action(action: str = Path(default=None, description="action name", example="http_action"),
                             current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Deletes the http action config and story event
    """
    try:
        mongo_processor.delete_http_action_config(action, user=current_user.get_user(),
                                                  bot=current_user.get_bot())
    except Exception as e:
        raise AppException(e)
    message = "HTTP action deleted"
    return Response(message=message)


@router.post("/action/slotset", response_model=Response)
async def add_slot_set_action(request_data: SlotSetActionRequest,
                              current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Stores the slot set action config.
    """
    mongo_processor.add_slot_set_action(request_data.dict(), current_user.get_bot(), current_user.get_user())
    return Response(message='Action added')


@router.get("/action/slotset", response_model=Response)
async def list_slot_set_actions(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Returns list of slot set actions for bot.
    """
    actions = mongo_processor.list_slot_set_actions(current_user.get_bot())
    return Response(data=actions)


@router.put("/action/slotset", response_model=Response)
async def edit_slot_set_action(request_data: SlotSetActionRequest,
                               current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Edits the slot set action config.
    """
    mongo_processor.edit_slot_set_action(request_data.dict(), current_user.get_bot(), current_user.get_user())
    return Response(message='Action updated')


@router.delete("/action/slotset/{action}", response_model=Response)
async def delete_slot_set_action(
        action: str = Path(default=None, description="action name", example="action_reset_slot"),
        current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Deletes the slot set action config.
    """
    mongo_processor.delete_action(action, current_user.get_bot(), current_user.get_user())
    return Response(message='Action deleted')


@router.get("/actions/logs", response_model=Response)
async def get_action_server_logs(start_idx: int = 0, page_size: int = 10, current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Retrieves action server logs for the bot.
    """
    logs = list(mongo_processor.get_action_server_logs(current_user.get_bot(), start_idx, page_size))
    row_cnt = mongo_processor.get_row_count(ActionServerLogs, current_user.get_bot())
    data = {
        "logs": logs,
        "total": row_cnt
    }
    return Response(data=data)


@router.post("/data/bulk", response_model=Response)
async def add_training_data(
        request_data: BulkTrainingDataAddRequest, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Adds intents, training examples and responses along with story against the responses
    """
    try:
        TrainingDataGenerationProcessor.validate_history_id(request_data.history_id)
        status, training_data_added = mongo_processor.add_training_data(
            training_data=request_data.training_data,
            bot=current_user.get_bot(),
            user=current_user.get_user(),
            is_integration=current_user.get_integration_status()
        )
        TrainingDataGenerationProcessor.update_is_persisted_flag(request_data.history_id, training_data_added)
    except Exception as e:
        raise AppException(e)
    return {"message": "Training data added successfully!", "data": status}


@router.put("/update/data/generator/status", response_model=Response)
async def update_training_data_generator_status(
        request_data: TrainingDataGeneratorStatusModel, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Update training data generator status
    """
    try:
        TrainingDataGenerationProcessor.retreive_response_and_set_status(request_data, current_user.get_bot(),
                                                                         current_user.get_user())
    except Exception as e:
        raise AppException(e)
    return {"message": "Status updated successfully!"}


@router.get("/data/generation/history", response_model=Response)
async def get_train_data_history(
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Fetches File Data Generation history, when and who initiated the process
    """
    file_history = TrainingDataGenerationProcessor.get_training_data_generator_history(current_user.get_bot())
    return {"data": {"training_history": file_history}}


@router.get("/data/generation/latest", response_model=Response)
async def get_latest_data_generation_status(
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Fetches status for latest data generation request
    """
    latest_data_generation_status = TrainingDataGenerationProcessor.fetch_latest_workload(current_user.get_bot(), current_user.get_user())
    return {"data": latest_data_generation_status}


@router.get("/slots", response_model=Response)
async def get_slots(
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Fetches status for latest data generation request
    """
    slots = list(mongo_processor.get_existing_slots(current_user.get_bot()))
    return {"data": slots}


@router.post("/slots", response_model=Response)
async def add_slots(
        request_data: SlotRequest,
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    adds a new slot
    :param request_data:
    :param current_user:
    :return: Success message with slot id
    """
    try:
        slot_value = request_data.dict()
        slot_id = mongo_processor.add_slot(slot_value=slot_value, bot=current_user.get_bot(), user=current_user.get_bot(), raise_exception_if_exists=True)
    except AppException as ae:
        raise AppException(str(ae))

    return {"message": "Slot added successfully!", "data": {"_id": slot_id}}


@router.delete("/slots/{slot}", response_model=Response)
async def delete_slots(
        slot: str = Path(default=None, description="slot name", example="bot"),
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    deletes an existing slot
    :param slot:
    :param current_user:
    :return: Success message
    """
    mongo_processor.delete_slot(slot_name=slot, bot=current_user.get_bot(), user=current_user.get_user())

    return {"message": "Slot deleted!"}


@router.put("/slots", response_model=Response)
async def edit_slots(
        request_data: SlotRequest,
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Updates an existing slot
    :param request_data:
    :param current_user:
    :return: Success message
    """
    try:
        slot_value = request_data.dict()
        mongo_processor.add_slot(slot_value=slot_value, bot=current_user.get_bot(), user=current_user.get_bot(), raise_exception_if_exists=False)
    except Exception as e:
        raise AppException(e)

    return {"message": "Slot updated!"}


@router.get("/importer/logs", response_model=Response)
async def get_data_importer_logs(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Get data importer event logs.
    """
    logs = list(DataImporterLogProcessor.get_logs(current_user.get_bot()))
    return Response(data=logs)


@router.post("/validate", response_model=Response)
async def validate_training_data(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Validates bot training data.
    """
    DataImporterLogProcessor.is_limit_exceeded(current_user.get_bot())
    DataImporterLogProcessor.is_event_in_progress(current_user.get_bot())
    Utility.make_dirs(os.path.join("training_data", current_user.get_bot(), str(uuid.uuid4())))
    DataImporterLogProcessor.add_log(current_user.get_bot(), current_user.get_user(), is_data_uploaded=False)
    background_tasks.add_task(EventsTrigger.trigger_data_importer,
                              current_user.get_bot(), current_user.get_user(),
                              False, False)
    return {"message": "Event triggered! Check logs."}


@router.get("/entity/synonyms", response_model=Response)
async def get_all_synonyms(
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Fetches the stored synonyms of the bot
    """
    synonyms = list(mongo_processor.fetch_synonyms(current_user.get_bot()))
    return {"data": synonyms}


@router.get("/entity/synonyms/{name}", response_model=Response)
async def get_synonym_values(
        name: str, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches list of values against synonym name
    """
    return {
        "data": list(mongo_processor.get_synonym_values(name, current_user.get_bot()))
    }


@router.post("/entity/synonyms", response_model=Response)
async def add_synonyms(
        request_data: SynonymRequest,
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    adds a new synonym and its values
    :param request_data:
    :param current_user:
    :return: Success message
    """

    mongo_processor.add_synonym(synonyms_dict=request_data.dict(), bot=current_user.get_bot(), user=current_user.get_user())

    return {"message": "Synonym and values added successfully!"}


@router.put("/entity/synonyms/{name}/{id}", response_model=Response)
async def edit_synonym(
        name: str,
        id: str,
        request_data: TextData,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Updates existing synonym value
    """
    mongo_processor.edit_synonym(
        id,
        request_data.data,
        name,
        current_user.get_bot(),
        current_user.get_user(),
    )
    return {
        "message": "Synonym updated!"
    }


@router.delete("/entity/synonyms/{delete_synonym}", response_model=Response)
async def delete_synonym_value(
        request_data: TextData,
        delete_synonym: bool = Path(default=False, description="Deletes synonym if True"),
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Deletes existing synonym completely along with its examples.
    """
    if delete_synonym:
        mongo_processor.delete_synonym(
            request_data.data, current_user.get_bot(), current_user.get_user()
        )
    else:
        mongo_processor.delete_synonym_value(
            request_data.data, current_user.get_bot(), current_user.get_user()
        )
    return {
        "message": "Synonym removed!"
    }


@router.post("/utterance", response_model=Response)
async def add_utterance(request: TextDataLowerCase, current_user: User = Depends(Authentication.get_current_user_and_bot)):
    mongo_processor.add_utterance_name(request.data, current_user.get_bot(), current_user.get_user(),
                                       raise_error_if_exists=True)
    return {'message': 'Utterance added!'}


@router.get("/utterance", response_model=Response)
async def get_utterance(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    return {'data': {"utterances": list(mongo_processor.get_utterances(current_user.get_bot()))}}


@router.get("/data/count", response_model=Response)
async def get_training_data_count(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    count = mongo_processor.get_training_data_count(current_user.get_bot())
    return Response(data=count)


@router.get("/chat/client/config/url", response_model=Response)
async def get_chat_client_config_url(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    access_token = Authentication.create_access_token(
        data={"sub": current_user.get_bot(), 'access-limit': ['/api/bot/.+/chat/client/config$']}, is_integration=True
    )
    url = urljoin(Utility.environment['app']['server_url'], f'/api/bot/{current_user.get_bot()}/chat/client/config/')
    url = urljoin(url, access_token)
    return Response(data=url)


@router.get("/chat/client/config/{uid}", response_model=Response)
async def get_client_config_using_uid(uid: str):
    decoded_uid = Utility.decode_limited_access_token(uid)
    config = mongo_processor.get_chat_client_config(decoded_uid['sub'])
    config = config.to_mongo().to_dict()
    return Response(data=config['config'])


@router.get("/chat/client/config", response_model=Response)
async def get_client_config(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    config = mongo_processor.get_chat_client_config(current_user.get_bot())
    config = config.to_mongo().to_dict()
    return Response(data=config['config'])


@router.post("/chat/client/config", response_model=Response)
async def set_client_config(request: DictData, current_user: User = Depends(Authentication.get_current_user_and_bot)):
    mongo_processor.save_chat_client_config(request.data, current_user.get_bot(), current_user.get_user())
    return {"message": "Config saved"}


@router.get("/regex", response_model=Response)
async def get_all_regex_patterns(
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches the stored regex patterns of the bot
    """
    regex = list(mongo_processor.fetch_regex_features(bot=current_user.get_bot()))
    return {"data": regex}


@router.post("/regex", response_model=Response)
async def add_regex(
        request_data: RegexRequest,
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    adds a new regex and its pattern
    :param request_data:
    :param current_user:
    :return: Success message
    """

    regex_id = mongo_processor.add_regex(regex_dict=request_data.dict(), bot=current_user.get_bot(), user=current_user.get_user())

    return {"message": "Regex pattern added successfully!", "data": {"_id": regex_id}}


@router.put("/regex", response_model=Response)
async def edit_regex(
        request_data: RegexRequest,
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    edits a regex pattern
    :param request_data:
    :param current_user:
    :return: Success message
    """

    mongo_processor.edit_regex(regex_dict=request_data.dict(), bot=current_user.get_bot(), user=current_user.get_user())

    return {"message": "Regex pattern modified successfully!"}


@router.delete("/regex/{name}", response_model=Response)
async def delete_regex(
        name: str = Path(default=None, description="regex name", example="bot"),
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    deletes an existing regex pattern
    :param name: regex pattern name
    :param current_user:
    :return: Success message
    """
    mongo_processor.delete_regex(regex_name=name, bot=current_user.get_bot(), user=current_user.get_user())

    return {"message": "Regex pattern deleted!"}


@router.get("/lookup/tables", response_model=Response)
async def get_all_lookup_tables(
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Fetches the stored lookup tables of the bot
    """
    lookup = list(mongo_processor.fetch_lookup_tables(bot=current_user.get_bot()))
    return {"data": lookup}


@router.get("/lookup/tables/{name}", response_model=Response)
async def get_lookup_values(
        name: str, current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches list of values against lookup table name
    """
    return {
        "data": list(mongo_processor.get_lookup_values(name, current_user.get_bot()))
    }


@router.post("/lookup/tables", response_model=Response)
async def add_lookup(
        request_data: LookupTablesRequest,
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    adds a new lookup table and its values
    :param request_data:
    :param current_user:
    :return: Success message
    """

    mongo_processor.add_lookup(lookup_dict=request_data.dict(), bot=current_user.get_bot(), user=current_user.get_user())

    return {"message": "Lookup table and values added successfully!"}


@router.put("/lookup/tables/{name}/{id}", response_model=Response)
async def edit_lookup(
        name: str,
        id: str,
        request_data: TextData,
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Updates existing lookup table value
    """
    mongo_processor.edit_lookup(
        id,
        request_data.data,
        name,
        current_user.get_bot(),
        current_user.get_user(),
    )
    return {
        "message": "Lookup table updated!"
    }


@router.delete("/lookup/tables/{delete_table}", response_model=Response)
async def delete_lookup_value(
        request_data: TextData,
        delete_table: bool = Path(default=False, description="Deletes lookup table if True"),
        current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Deletes existing lookup table completely along with its examples.
    """
    if delete_table:
        mongo_processor.delete_lookup(
            request_data.data, current_user.get_bot(), current_user.get_user()
        )
    else:
        mongo_processor.delete_lookup_value(
            request_data.data, current_user.get_bot(), current_user.get_user()
        )
    return {
        "message": "Lookup Table removed!"
    }


@router.post("/forms", response_model=Response)
async def add_form(request: Forms, current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Adds a new form.
    """
    mongo_processor.add_form(request.name, request.dict()['path'], current_user.get_bot(), current_user.get_user())
    return Response(message='Form added')


@router.get("/forms", response_model=Response)
async def list_forms(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Lists all forms in the bot.
    """
    forms = mongo_processor.list_forms(current_user.get_bot())
    return Response(data=forms)


@router.get("/forms/{form_name}", response_model=Response)
async def get_form(form_name: str = Path(default=None, description="Name of the form"),
                   current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Get a particular form.
    """
    form = mongo_processor.get_form(form_name, current_user.get_bot())
    return Response(data=form)


@router.put("/forms", response_model=Response)
async def edit_form(request: Forms, current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Edits a form.
    """
    mongo_processor.edit_form(request.name, request.dict()['path'], current_user.get_bot(), current_user.get_user())
    return Response(message='Form updated')


@router.delete("/forms", response_model=Response)
async def delete_form(request: TextData, current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Deletes a form and its associated utterances.
    """
    mongo_processor.delete_form(request.data, current_user.get_bot(), current_user.get_user())
    return Response(message='Form deleted')


@router.get("/entities", response_model=Response)
async def list_entities(current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetch entities registered in a bot.
    """
    return Response(data=mongo_processor.get_entities(current_user.get_bot()))

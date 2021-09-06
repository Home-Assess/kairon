from typing import Text

from fastapi import APIRouter
from fastapi import Depends, Query
from starlette.responses import StreamingResponse
from io import BytesIO

from kairon.api.models import Response
from kairon.shared.auth import Authentication
from kairon.shared.models import User
from kairon.shared.utils import Utility
from kairon.shared.data.utils import DataUtility

router = APIRouter()


@router.get("/users", response_model=Response)
async def chat_history_users(month: int = Query(default=1, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):

    """
    Fetches the list of user who has conversation with the agent
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/conversations/users',
        {'month': month}
    )


@router.get("/users/{sender}", response_model=Response)
async def chat_history(
    sender: Text, month: int = Query(default=1, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)
):
    """
    Fetches the list of conversation with the agent by particular user
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/conversations/users/{sender}',
        {'month': month}
    )


@router.get("/metrics/users", response_model=Response)
async def user_with_metrics(
        month: int = Query(default=1, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the list of user who has conversation with the agent with steps anf time
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/metrics/users',
        {'month': month}
    )


@router.get("/metrics/fallback", response_model=Response)
async def visitor_hit_fallback(month: int = Query(default=1, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the number of times the agent hit a fallback (ie. not able to answer) to user queries
    """
    fallback_action, nlu_fallback_action = DataUtility.load_fallback_actions(current_user.get_bot())
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/metrics/fallback',
        {'month': month, 'action_fallback': fallback_action, 'nlu_fallback': nlu_fallback_action}
    )


@router.get("/metrics/conversation/steps", response_model=Response)
async def conversation_steps(month: int = Query(default=1, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
     Fetches the number of conversation steps that took place in the chat between the users and the agent
     """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/metrics/conversation/steps',
        {'month': month}
    )


@router.get("/metrics/conversation/time", response_model=Response)
async def conversation_time(month: int = Query(default=1, ge=2, le=6),current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the duration of the chat that took place between the users and the agent"""
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/metrics/conversation/time',
        {'month': month}
    )


@router.get("/metrics/user/engaged", response_model=Response)
async def count_engaged_users(month: int = Query(default=1, ge=2, le=6), conversation_step_threshold: int = 10,
                              current_user: User = Depends(Authentication.get_current_user_and_bot)):

    """
    Fetches the number of engaged users of the bot
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/metrics/users/engaged',
        {'month': month, 'conversation_step_threshold': conversation_step_threshold}
    )


@router.get("/metrics/user/new", response_model=Response)
async def count_new_users(month: int = Query(default=1, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the number of new users of the bot
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/metrics/users/new',
        {'month': month}
    )


@router.get("/metrics/conversation/success", response_model=Response)
async def complete_conversations(month: int = Query(default=1, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the number of successful conversations of the bot, which had no fallback
    """
    fallback_action, nlu_fallback_action = DataUtility.load_fallback_actions(current_user.get_bot())
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/metrics/conversation/success',
        {'month': month, 'action_fallback': fallback_action, 'nlu_fallback': nlu_fallback_action}
    )


@router.get("/metrics/user/retention", response_model=Response)
async def calculate_retention(month: int = Query(default=1, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the user retention percentage of the bot
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/metrics/users/retention',
        {'month': month}
    )


@router.get("/metrics/trend/user/engaged", response_model=Response)
async def engaged_users_trend(month: int = Query(default=6, ge=2, le=6),
                              conversation_step_threshold: int = 10,
                              current_user: User = Depends(Authentication.get_current_user_and_bot)):

    """
    Fetches the counts of engaged users of the bot for previous months
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/trends/users/engaged',
        {'month': month, 'conversation_step_threshold': conversation_step_threshold}
    )


@router.get("/metrics/trend/user/new", response_model=Response)
async def new_users_trend(month: int = Query(default=6, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the counts of new users of the bot for previous months
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/trends/users/new',
        {'month': month}
    )


@router.get("/metrics/trend/conversation/success", response_model=Response)
async def complete_conversation_trend(month: int = Query(default=6, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the counts of successful conversations of the bot for previous months
    """
    fallback_action, nlu_fallback_action = DataUtility.load_fallback_actions(current_user.get_bot())
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/trends/conversations/success',
        {'month': month, 'action_fallback': fallback_action, 'nlu_fallback': nlu_fallback_action}
    )


@router.get("/metrics/trend/user/retention", response_model=Response)
async def retention_trend(month: int = Query(default=6, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the counts of user retention percentages of the bot for previous months
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/trends/users/retention',
        {'month': month}
    )


@router.get("/metrics/trend/user/fallback", response_model=Response)
async def fallback_trend(month: int = Query(default=6, ge=2, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the fallback count of the bot for previous months
    """
    fallback_action, nlu_fallback_action = DataUtility.load_fallback_actions(current_user.get_bot())
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/trends/fallback',
        {'month': month, 'action_fallback': fallback_action, 'nlu_fallback': nlu_fallback_action}
    )


@router.get("/conversations", response_model=Response)
async def flat_conversations(month: int = Query(default=1, ge=1, le=6), current_user: User = Depends(Authentication.get_current_user_and_bot)):
    """
    Fetches the flattened conversation data of the bot for previous months
    """
    return Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/conversations',
        {'month': month}
    )


@router.get("/conversations/download")
async def download_conversations(
        month: int = Query(default=1, ge=1, le=6),
        current_user: User = Depends(Authentication.get_current_user_and_bot),
):
    """
    Downloads conversation history of the bot, for the specified months
    """
    response = Utility.trigger_history_server_request(
        current_user.get_bot(),
        f'/api/history/{current_user.get_bot()}/conversations/download',
        {'month': month}, return_json=False
    )
    return StreamingResponse(BytesIO(response.content), headers=response.headers)

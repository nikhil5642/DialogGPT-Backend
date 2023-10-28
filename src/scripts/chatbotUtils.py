from src.DataBaseConstants import ESSENTIALS_PLAN, PRO_PLAN, BASIC_PLAN,MONTHLY


def getChatBotLimitAsPerPlan(plan):
    if plan==PRO_PLAN:
        return 5
    elif plan==ESSENTIALS_PLAN:
        return 2
    elif plan==BASIC_PLAN:
        return 1
    else:
        return 0

def getMessageLimitAsPerPlan(plan,duration):
    if plan==PRO_PLAN:
        return 10000 if duration==MONTHLY  else 120000
    elif plan==ESSENTIALS_PLAN:
        return 5000 if duration==MONTHLY  else 60000
    elif plan==BASIC_PLAN:
        return 2000 if duration==MONTHLY  else 24000
    else:
        return 0


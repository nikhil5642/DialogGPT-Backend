from src.DataBaseConstants import ESSENTIALS_PLAN, PRO_PLAN


def getChatBotLimitAsPerPlan(plan):
    if plan==PRO_PLAN:
        return 5
    elif plan==ESSENTIALS_PLAN:
        return 2
    else:
        return 1

def getMessageLimitAsPerPlan(plan):
    if plan==PRO_PLAN:
        return 10000
    elif plan==ESSENTIALS_PLAN:
        return 2000
    else:
        return 30

NOTE: I temporarily disabled the webhook. So to run the entire script, just run `listener.py`. 

When running, you can test by:

1. Connecting your Telegram account.
2. Selecting the channel I added you to (`mt5 bot test`).
3. Simulating trading messages and update messages.

Here are the chores:

1. The update trade functionality is lacking certain things:
    - In `listener.py`, you will find the function for parsing update messages from the group, `parse_update_instruction`. It has to be able to parse other variations as well. For instance:
      ```
      Change entry to 3129
      And SL to 3119
      ```
      It should be able to extract the adjustments of SL and entry accordingly when parsing.
    - In `mt5.utils`, you will find the function to update trade. The trade action used there only works for orders that are already running. Pending orders use `TRADE_ACTION_MODIFY`, so we need to be able to check the order status.

2. Close trade request needs to be updated:
    - In the same `mt5.utils` `update_trade` function, we can change how the trade is closed. For pending orders, we should use `TRADE_ACTION_REMOVE`, and for running orders, `TRADE_ACTION_CLOSE_BY`. (https://www.mql5.com/en/docs/python_metatrader5/mt5ordercheck_py#trade_request_actions)

3. Move to live account — that will require login.

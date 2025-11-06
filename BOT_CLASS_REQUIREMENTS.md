# Bot Class Requirements

**Recorded:** 2025-11-05 22:03

## User Requirements

Here's what I want you to focus on:

1. **Create the bot class**

2. **Allow it to make a mock API request to an AI API like Gemini, and get a mock response back, in some kind of promise / async handoff of information**

3. **Have a system that records all the data going in and out of the bot class**

4. **Have the bot class have a memory it can couple to, so that it can access a database and extract information from it. This should be in 2 parts: internal (permanent) memory and external (modular) memory**

5. **It should have an ongoing journal of internal thoughts, like a log of its thinking, to be stored in a queryable database with a complete and comprehensive data structure and complete logical labeling and tagging of the thought patterns to examine the various paths it has considered over time**

6. **It should be able to search a database of requests, to see if the user's specific request has been submitted before word-for-word**

7. **It should be able to look up past attempts to respond to a matched prompt, choose whether or not to make a new attempt, and add any new attempt to the records**

8. **It should be able to record new requests if they are not an exact match**

9. **It should be able to be smart enough to find adjacent prompts that are similar enough to the current prompt if there are any**

10. **It should have all of this stored in a single folder, the bot's working folder. There should be an internal (permanent) working folder and an external (modular) (pointable) working folder with SAFETY PROTOCOLS FIRMLY IN PLACE before read or write or coupling to any external folder. You need to make sure it's in the same workspace, or the same directory, and if it's not, get the directory path, and if it's in the same general project, that should be fine, but if it's outside the root of where the bot is, then it should be disabled by default with user permission to access and read / write / CRUD operations with a permission granting structure on a per folder basis outside the bot**

11. **All of this should be logged and recorded, and the AI bot should reflect on its actions as it takes them.**


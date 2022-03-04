# Chatbot Dining Concierge

Customer Service is a core service for a lot of businesses around the world and it is getting disrupted at the moment by Natural Language Processing-powered applications. We have implemented a serverless, microservice-driven web application. Specifically, a Dining Concierge chatbot that sends you restaurant suggestions given a set of preferences that you provide the chatbot with through conversation.

![image](https://user-images.githubusercontent.com/55443909/156676448-472f9f31-93c0-4bc0-b94a-a6510f2996c7.png)

# AWS Services used:
- Simple Storage Service (S3)
- API Gateway
- Lambda
- Lex
- Simple Queue Service (SQS)
- DynamoDb
- OpenSearch
- Simple Email Service (SES)
- CloudWatch

In summary, based on a conversation with the customer, the Amazon LEX chatbot will identify the customer’s preferred ‘cuisine’. It will search through ElasticSearch to get random suggestions of restaurant IDs with this cuisine. At this point, you would also need to query the DynamoDB table with these restaurant IDs to find more information about the restaurants you want to suggest to your customers like name and address of the restaurant. 

A state for the concierge application has been created, such that it remembers your last search for both location and category. When a user returns to the chat, it should automatically receive a recommendation based on their previous search. DynamoDB has been used to store intermediary state information and a separate Lambda function to handle the recommendation based on the last search.


# Example Interaction 

User: Hello

Bot: Hi there, how can I help?

User: I need some restaurant suggestions.

Bot: Great. I can help you with that. What city or city area are you looking to dine in?

User: Manhattan

Bot: Got it, Manhattan. What cuisine would you like to try?

User: Japanese

Bot: Ok, how many people are in your party?

User: 2

Bot: A few more to go. What date?

User: 17th

Bot: What time?

User: 16:00

Bot: What is your email address?

User: xxxxxx @ gmail.com

Bot: Great. Lastly, I need your phone number so I can send you my findings.

User: 123-456-7890

Bot: You’re all set. Expect my suggestions shortly! Have a good day.

User: Thank you!

Bot: Happy to help!

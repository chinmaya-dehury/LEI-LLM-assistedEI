# Basic control Flow

![Basic Control Flow](controlFlow.png)

Prompt
============  

1-------------
This is the control flow of LLM-assisted Edge Intelligence.

2-------------
Based on this I want to implement a proof-of-concept. I want to consider environmental or traffic data. I want to use Python language. How shall I proceed?


3----------
Lets go with the environmental data : Edge device periodically measures temperature & humidity. Prepare the data, metadata, and the context. These will be given to LLM so that LLM can understand the sample data, metadata and the context and based on its understanding it can give the code for insight.


4---------------
yes. I confirm. Also please remember that the LLM may generate x number of programs. We dont not know, the number of programs.

5-----------
now prepare the edge_executor.py that: 
-> Automatically runs all generated programs in generated_tasks/ 
-> Logs results and execution times (simulating edge device behavior)?


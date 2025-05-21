import asyncio
import csv
import logging
from ollama import AsyncClient

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_output(output):
    lines = output.split('\n')
    result = {'Score': None, 'Recommendation': ''}
    try:
        for line in lines:
            if "I'd give this prompt a score of" in line:
                result['Score'] = int(line.split()[-1])
            elif "To improve the prompt," in line:
                recommendation_lines = lines[lines.index(line)+1:]
                result['Recommendation'] = ' '.join(recommendation_lines).strip()
                break
    except Exception as e:
        logging.error(f"Failed to parse output: {e}")
    
    if result['Score'] is None or not result['Recommendation']:
        logging.error("Parsed result does not contain both 'Score' and 'Recommendation'.")
    
    logging.info(f"Parsed Result: {result}")
    return result


async def chat(prompt):
    message = {
        'role': 'user',
        'content': f'''Evaluate the following stock prediction prompt and provide a score (0-99) along with recommendations for making it more precise: "{prompt}"'''
    }

    for attempt in range(3):  # 重試3次
        try:
            response = await AsyncClient().chat(model='llama3:8b', messages=[message], stream=True, options={"temperature": 0.8})
            break
        except Exception as e:
            logging.error(f"Failed to get response from model: {e}")
            await asyncio.sleep(2 ** attempt)  # 指數級退避
    else:
        logging.error("Exceeded maximum retry attempts")
        return None

    output = ''
    try:
        async for part in response:
            output += part['message']['content']
    except Exception as e:
        logging.error(f"Error during streaming response: {e}")
        return None

    with open('output_prompt.txt', 'a', encoding='utf-8') as f:
        f.write(output + '\n')

    parsed_result = parse_output(output)

    return parsed_result


def generate_variation(prompt, recommendation):
    if recommendation:
        new_prompt = f"{prompt}\n\n{recommendation}"
        # 簡單驗證生成的prompt是否合理
        if len(new_prompt) > 5000:  # 假設最大長度為5000字符
            logging.warning("Generated prompt is too long.")
            return prompt
        return new_prompt
    else:
        logging.warning("No recommendation provided to generate variation.")
        return prompt

async def main():
    initial_prompt = """Evaluate the stock price of XYZ Inc. (2330) based on the following data:
    * Current price: 
    * BPS (book value per share): 
    * Capital: 
    * ROE (return on equity): 


    Provide additional context about the company, industry, and market trends.

Assume you are a stock analyst, provide answers to the following questions (Only answer the following questions, do not give suggestions or analysis):

1. Will it be bullish or bearish in the next six months?
2. Recommended buying price, considering a margin of error of +/- 5%?
3. Recommended selling price, assuming a stop-loss strategy with a maximum loss of 10%?
4. Recommended holding period for this investment?(months)
5. Suggested stop-loss strategy? What would be your criteria for triggering a sell order?

Criteria for evaluation:

* A "bullish" market is defined as an increase of at least 10% in the stock's price over the next six months.
* A "bearish" market is defined as a decrease of at least 15% in the stock's price over the next six months.
* If it is bullish, usually the selling price will be higher than the buying price. 
* If it is bearish, you do not need to answer question 2.3.4.5
* The Recommended selling price should be the take-profit price when bullish. If the former is bearish, it can be skipped directly.

Answer according to the example format, do not explain
answer example format:
1. Will it be bullish or bearish in the next six months?: Bullish/Bearish
2. Recommended buying price, considering a margin of error of +/- 5%?: [a integer] NTD
3. Recommended selling price, assuming a stop-loss strategy with a maximum loss of 10%?: [a integer] NTD
4. Recommended holding period for this investment? (months): [a integer] months
5. Suggested stop-loss strategy? What would be your criteria for triggering a sell order?: [strategy]
"""

    max_iterations = 10
    convergence_threshold = 85  # 如果得分达到或超过这个值，则认为已经收敛
    for i in range(max_iterations):
        logging.info(f"Iteration {i+1}")
        result = await chat(initial_prompt)
        if result and 'Recommendation' in result:
            score = result['Score']
            recommendation = result['Recommendation']
            if score is not None and score >= convergence_threshold:
                logging.info(f"Convergence reached with score: {score}")
                break
            initial_prompt = generate_variation(initial_prompt, recommendation)
        else:
            logging.error("No valid result to generate variation from.")
            break

        print(f"Iteration {i+1} - Score: {score}")
        print(f"Updated Prompt: {initial_prompt}")

asyncio.run(main())

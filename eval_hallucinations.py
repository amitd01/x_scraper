import os
import anthropic

def run_eval(source_text: str, summary_text: str):
    print("Running Generative Eval with Claude 3 Haiku...")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""
    You are an impartial executive evaluator verifying an AI pipeline.
    Your job is to read the original SOURCE TEXT and the resulting GENERATED SUMMARY.
    
    Task:
    1. Check for **Hallucinations**: Does the summary contain any specific claims, numbers, or facts NOT present in the source text?
    2. Check for **Accuracy**: Does the summary accurately reflect the primary point of the source?
    
    SOURCE TEXT:
    {source_text}
    
    GENERATED SUMMARY:
    {summary_text}
    
    Respond in the following format:
    HALLUCINATIONS: [None / Yes (explain)]
    ACCURACY: [Pass / Fail (explain)]
    OVERALL GRADE: [A/B/C/D/F]
    """
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            temperature=0.0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        result = message.content[0].text
        print("\n=== EVALUATION REPORT ===")
        print(result)
        print("=========================\n")
    except Exception as e:
        print(f"Eval Error: {e}")

if __name__ == "__main__":
    # Example test payload demonstrating the LLM's ability to catch a hallucinated stat
    sample_source = "In Q3 2023, the startup successfully rolled out the new feature to 10,000 customers. Conversion rates increased by 12%."
    sample_summary = "The startup saw incredible growth in Q3 2023, rolling out to 10,000 customers and boosting conversion rates by 25% due to the AI implementation."
    
    print(f"Testing Eval Script on known hallucinated summary ...")
    print(f"Source: {sample_source}")
    print(f"Summary: {sample_summary}")
    
    run_eval(sample_source, sample_summary)

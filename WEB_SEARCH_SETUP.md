# Web Search Setup for Autonomous AI

The AI now has real-time web search capabilities to look up professional standards, building codes, and best practices during analysis.

## Setup Instructions

### 1. Get Tavily API Key

1. Go to https://tavily.com
2. Sign up for a free account
3. Get your API key from the dashboard
4. Free tier includes 1,000 searches/month

### 2. Set Environment Variable

Add to your `.env` file or environment:

```bash
TAVILY_API_KEY=your_tavily_api_key_here
```

On Render/production:
1. Go to your Render dashboard
2. Navigate to Environment
3. Add new environment variable:
   - Key: `TAVILY_API_KEY`
   - Value: Your Tavily API key

### 3. Install Dependencies

The required package is already in `requirements.txt`:

```bash
tavily-python==0.5.0
```

When you deploy, Render will automatically install it.

## How It Works

### Autonomous AI Agent

The AI is now truly autonomous. Instead of following static instructions, it:

1. **Receives the floor plan** image
2. **Thinks** about what it needs to know
3. **Searches the web** for specific information (e.g., "NEC outlet spacing requirements")
4. **Receives** search results with current code standards
5. **Thinks more** with the new knowledge
6. **Searches again** if needed
7. **Provides** accurate analysis based on real-world standards

### Example Workflow

```
USER: Upload floor plan for electrical analysis

AI: "I need to understand NEC outlet spacing requirements"
    → Searches: "NEC code 210.52 outlet spacing requirements"
    → Gets results from electrician resources

AI: "Now I need to verify GFCI requirements for kitchen"
    → Searches: "NEC GFCI requirements kitchen 2023"
    → Gets current code requirements

AI: "Let me check typical room dimensions to validate scale"
    → Searches: "typical bedroom dimensions residential"
    → Gets standard measurements

AI: Provides analysis with:
    - Accurate outlet placement per NEC 210.52
    - GFCI outlets within 6 feet of sink
    - Proper switch placement per code
    - All positions validated against real standards
```

### What AI Can Search

The AI autonomously searches for:

- **Building Codes**: NEC electrical codes, local building codes, ADA requirements
- **Professional Standards**: Electrician best practices, installer guidelines, industry standards
- **Component Placement**: Where keypads go, switch heights, outlet spacing
- **Safety Requirements**: GFCI locations, arc-fault requirements, clearances
- **Common Sense**: Typical room sizes, standard practices, logical placement
- **Symbol Standards**: Electrical symbol meanings, architectural conventions

### Benefits

1. **Always Current**: Gets latest code requirements, not outdated static info
2. **More Accurate**: Verifies placement against real-world standards
3. **Truly Intelligent**: Reasons about what it needs to know and looks it up
4. **No Hallucination**: Can verify uncertain information instead of guessing
5. **Professional Quality**: Matches licensed electrician knowledge level

### Monitoring

When AI searches, you'll see console output:

```
🔍 AI searching: NEC code outlet spacing requirements residential
🔍 AI searching electrical codes: light switch height ADA code
```

This shows the AI is actively researching during analysis.

### Cost

- **Tavily Free Tier**: 1,000 searches/month (plenty for most usage)
- **Each Analysis**: Typically 3-8 searches
- **Monthly Capacity**: ~125-330 floor plan analyses on free tier

### Fallback

If Tavily API key is not set:
- AI still works but uses embedded knowledge only
- Warning message: "Web search features will be limited"
- Analysis proceeds with static professional standards

## Architecture

### Tool Use Pattern

```python
# AI gets the floorplan
AI: "I want to search for something"

# System executes search
System: Calls Tavily API → Returns results

# AI reads results
AI: "Now I understand! Let me search for more..."

# Loop continues until AI has enough information
# Then AI provides final analysis
```

### Agentic Loop

The system implements an agentic loop:

```python
while not done:
    response = ai.analyze(image, conversation_history)

    if response.wants_tool_use:
        tool_results = execute_tools(response.tool_calls)
        conversation_history.append(tool_results)
        continue  # AI gets results and thinks more

    if response.is_complete:
        return response.analysis
```

## Testing

To test if web search is working:

1. Upload a floor plan
2. Check console/logs for search queries:
   ```
   🔍 AI searching: [query]
   ```
3. Analysis should include code-compliant placements

## Troubleshooting

### "Web search features will be limited"
- Tavily API key not set
- Set `TAVILY_API_KEY` environment variable

### "Tavily API error"
- Invalid API key
- Rate limit exceeded (>1000/month on free tier)
- Check API key is correct

### AI not searching
- Check console for search queries
- AI might have enough embedded knowledge
- Try more complex/ambiguous floor plans

## Future Enhancements

Potential additions:
- Code-specific databases (NEC direct access)
- Local building code lookups by location
- Historical code versions for renovation projects
- Multi-language code support (international standards)

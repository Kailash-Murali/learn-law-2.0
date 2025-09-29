import asyncio
from ik_api_async import AsyncIKApi

# Replace with your Indian Kanoon API token!
IK_API_TOKEN = "abbb21b37c3bbc1458ae370c7cae561720e50a87"

async def test_kanoon_api():
    ikapi = AsyncIKApi(IK_API_TOKEN)

    # Test 1: Case Law Search (Article 21)
    print("Testing case law search for 'article 21'...")
    results = await ikapi.search('article 21', doctype="judgments", maxpages=1)
    print("Raw API Response:", results)

    docs = results.get("docs", [])
    print(f"Documents found: {len(docs)}")
    if docs:
        for doc in docs[:3]:  # Print first 3 docs
            print({ "title": doc.get("title"), "court": doc.get("docsource"), "publishdate": doc.get("publishdate"), "url": f"https://indiankanoon.org/doc/{doc['tid']}/" })

    # Test 2: Statute Search (Protection of Women from Domestic Violence Act)
    print("\nTesting statute search for 'Protection of Women from Domestic Violence Act'...")
    results = await ikapi.search('Protection of Women from Domestic Violence Act', doctype="acts", maxpages=1)
    print("Raw API Response:", results)

    docs = results.get("docs", [])
    print(f"Documents found: {len(docs)}")
    if docs:
        for doc in docs[:3]:
            print({ "title": doc.get("title"), "court": doc.get("docsource"), "publishdate": doc.get("publishdate"), "url": f"https://indiankanoon.org/doc/{doc['tid']}/" })

if __name__ == "__main__":
    asyncio.run(test_kanoon_api())

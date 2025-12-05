"""Quick script to check Neo4j database stats."""
import asyncio
from app.repositories.neo4j_repository import Neo4jRepository
from app.config import settings

async def main():
    # Connect to Neo4j
    repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    await repo.connect()
    
    print("🔍 Checking Neo4j Database Stats...")
    print("=" * 50)
    
    stats = await repo.get_database_stats()
    
    print(f"\n📊 Current Data:")
    print(f"  Skills:        {stats['skills_count']:,}")
    print(f"  Jobs:          {stats['jobs_count']:,}")
    print(f"  Companies:     {stats['companies_count']:,}")
    print(f"  Locations:     {stats['locations_count']:,}")
    print(f"  Categories:    {stats['categories_count']:,}")
    print(f"  Subcategories: {stats['subcategories_count']:,}")
    print(f"  Relationships: {stats['relationships_count']:,}")
    
    total_nodes = sum([
        stats['skills_count'],
        stats['jobs_count'],
        stats['companies_count'],
        stats['locations_count'],
        stats['categories_count'],
        stats['subcategories_count']
    ])
    
    print(f"\n📈 Total Nodes: {total_nodes:,}")
    print("=" * 50)
    
    # Ask if user wants to delete
    if total_nodes > 0:
        print("\n⚠️  WARNING: Database contains data from previous uploads")
        print("   - 1,997 skills from the stuck job")
        print("   - These will be UPDATED (not duplicated) on new upload")
        print("   - To start fresh, you can delete all data")
        
        delete = input("\n🗑️  Delete ALL data and start fresh? (yes/NO): ").strip().lower()
        
        if delete == 'yes':
            print("\n⏳ Deleting all data...")
            result = await repo.delete_all_data()
            print(f"✅ Deleted {result['nodes_deleted']:,} nodes")
            print("✅ Database is now empty")
        else:
            print("\n✅ Data preserved - new uploads will update existing records")
    else:
        print("\n✅ Database is empty - ready for fresh upload")
    
    await repo.close()

if __name__ == "__main__":
    asyncio.run(main())

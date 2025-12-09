#!/usr/bin/env python3
"""Database migration runner script.

Usage:
    python db/migrate.py           # Run pending migrations
    python db/migrate.py --fresh   # Drop all tables, re-run all migrations
    python db/migrate.py --status  # Show migration status
    python db/migrate.py --rollback # Rollback last migration
"""

import argparse
import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

import asyncpg

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings  # noqa: E402


class MigrationRunner:
    """Database migration runner."""

    def __init__(self, database_url: str):
        """Initialize migration runner.

        Args:
            database_url: PostgreSQL database URL.
        """
        # Convert SQLAlchemy URL to asyncpg format
        self.database_url = database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.conn: asyncpg.Connection | None = None

    async def connect(self) -> None:
        """Connect to the database."""
        self.conn = await asyncpg.connect(self.database_url)

    async def close(self) -> None:
        """Close database connection."""
        if self.conn:
            await self.conn.close()

    async def ensure_migrations_table(self) -> None:
        """Ensure schema_migrations table exists."""
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

    async def get_executed_migrations(self) -> dict[str, datetime]:
        """Get list of executed migrations.

        Returns:
            Dict mapping version to execution timestamp.
        """
        rows = await self.conn.fetch(
            "SELECT version, executed_at FROM schema_migrations ORDER BY version"
        )
        return {row["version"]: row["executed_at"] for row in rows}

    def get_migration_files(self) -> list[tuple[str, Path]]:
        """Get list of migration files sorted by version.

        Returns:
            List of (version, path) tuples sorted by version.
        """
        migrations = []
        pattern = re.compile(r"^(V\d{4}_\d{2}_\d{2}_\d{3})__.*\.sql$")

        for file in self.migrations_dir.glob("*.sql"):
            match = pattern.match(file.name)
            if match:
                version = match.group(1)
                migrations.append((version, file))

        return sorted(migrations, key=lambda x: x[0])

    async def get_pending_migrations(self) -> list[tuple[str, Path]]:
        """Get list of pending migrations.

        Returns:
            List of (version, path) tuples for pending migrations.
        """
        executed = await self.get_executed_migrations()
        all_migrations = self.get_migration_files()
        return [(v, p) for v, p in all_migrations if v not in executed]

    def extract_rollback_sql(self, content: str) -> str | None:
        """Extract rollback SQL from migration file.

        Args:
            content: Migration file content.

        Returns:
            Rollback SQL if found, None otherwise.
        """
        # Look for -- ROLLBACK: marker
        rollback_marker = "-- ROLLBACK:"
        if rollback_marker not in content:
            return None

        # Extract everything after the marker
        idx = content.index(rollback_marker)
        rollback_section = content[idx + len(rollback_marker) :]

        # Remove comment prefixes and clean up
        lines = []
        for line in rollback_section.strip().split("\n"):
            line = line.strip()
            if line.startswith("-- "):
                lines.append(line[3:])
            elif line.startswith("--"):
                lines.append(line[2:])
            elif line and not line.startswith("--"):
                # Stop at non-comment line that's not empty
                break

        return "\n".join(lines).strip() if lines else None

    async def run_migration(self, version: str, path: Path) -> bool:
        """Run a single migration.

        Args:
            version: Migration version.
            path: Path to migration file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            content = path.read_text()

            # Extract only the UP migration (exclude rollback section)
            rollback_marker = "-- ROLLBACK:"
            if rollback_marker in content:
                up_sql = content[: content.index(rollback_marker)].strip()
            else:
                up_sql = content

            # Execute migration
            await self.conn.execute(up_sql)

            # Record migration (skip for bootstrap migration)
            if version != "V0000_00_00_000":
                await self.conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name)
                    VALUES ($1, $2)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    version,
                    path.name,
                )
            else:
                # For bootstrap, still record it
                await self.conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name)
                    VALUES ($1, $2)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    version,
                    path.name,
                )

            return True
        except Exception as e:
            print(f"  Error: {e}")
            return False

    async def run_pending(self) -> int:
        """Run all pending migrations.

        Returns:
            Number of migrations executed.
        """
        await self.ensure_migrations_table()
        pending = await self.get_pending_migrations()

        if not pending:
            print("No pending migrations.")
            return 0

        print("Running migrations...")
        count = 0

        for version, path in pending:
            print(f"  Running {path.name}...", end=" ")
            if await self.run_migration(version, path):
                print("✓")
                count += 1
            else:
                print("✗")
                print(f"\nMigration failed at {path.name}. Stopping.")
                break

        print(f"\nDone! {count} migration(s) executed.")
        return count

    async def get_all_tables(self) -> list[str]:
        """Get list of all user tables in database.

        Returns:
            List of table names.
        """
        rows = await self.conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename != 'schema_migrations'
        """)
        return [row["tablename"] for row in rows]

    async def run_fresh(self, force: bool = False) -> int:
        """Drop all tables and re-run all migrations.

        Args:
            force: Skip confirmation prompt.

        Returns:
            Number of migrations executed.
        """
        if not force:
            response = input(
                "WARNING: This will drop ALL tables and data. Continue? [y/N]: "
            )
            if response.lower() != "y":
                print("Aborted.")
                return 0

        print("Dropping all tables...")

        # Get all tables including schema_migrations
        rows = await self.conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """)
        tables = [row["tablename"] for row in rows]

        if tables:
            # Drop all tables with CASCADE
            for table in tables:
                await self.conn.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                print(f"  Dropped {table}")

        # Also drop any functions we created
        await self.conn.execute(
            "DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE"
        )

        print("\nRunning all migrations...")
        await self.ensure_migrations_table()

        all_migrations = self.get_migration_files()
        count = 0

        for version, path in all_migrations:
            print(f"  Running {path.name}...", end=" ")
            if await self.run_migration(version, path):
                print("✓")
                count += 1
            else:
                print("✗")
                print(f"\nMigration failed at {path.name}. Stopping.")
                break

        print(f"\nDone! {count} migration(s) executed.")
        return count

    async def show_status(self) -> None:
        """Show migration status."""
        await self.ensure_migrations_table()

        executed = await self.get_executed_migrations()
        all_migrations = self.get_migration_files()

        print("\nMigration Status")
        print("=" * 60)

        if not all_migrations:
            print("No migration files found.")
            return

        for version, path in all_migrations:
            if version in executed:
                timestamp = executed[version].strftime("%Y-%m-%d %H:%M:%S")
                print(f"  ✓ {path.name}")
                print(f"    executed: {timestamp}")
            else:
                print(f"  ○ {path.name}")
                print("    pending")

        print()
        pending_count = len([v for v, _ in all_migrations if v not in executed])
        executed_count = len(executed)
        print(f"Total: {len(all_migrations)} migrations")
        print(f"  Executed: {executed_count}")
        print(f"  Pending: {pending_count}")

    async def rollback_last(self) -> bool:
        """Rollback the last executed migration.

        Returns:
            True if successful, False otherwise.
        """
        await self.ensure_migrations_table()

        # Get last executed migration
        row = await self.conn.fetchrow("""
            SELECT version, name FROM schema_migrations
            ORDER BY executed_at DESC, version DESC
            LIMIT 1
        """)

        if not row:
            print("No migrations to rollback.")
            return False

        version = row["version"]
        name = row["name"]

        # Don't allow rolling back the bootstrap migration
        if version == "V0000_00_00_000":
            print("Cannot rollback the bootstrap migration.")
            return False

        # Find the migration file
        migration_path = self.migrations_dir / name
        if not migration_path.exists():
            print(f"Migration file not found: {name}")
            return False

        # Extract rollback SQL
        content = migration_path.read_text()
        rollback_sql = self.extract_rollback_sql(content)

        if not rollback_sql:
            print(f"No rollback SQL found in {name}")
            print("Add a -- ROLLBACK: section to the migration file.")
            return False

        print(f"Rolling back {name}...")

        try:
            # Execute rollback
            await self.conn.execute(rollback_sql)

            # Remove from tracking table
            await self.conn.execute(
                "DELETE FROM schema_migrations WHERE version = $1", version
            )

            print("✓ Rollback successful")
            return True
        except Exception as e:
            print(f"✗ Rollback failed: {e}")
            return False


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database migration runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python db/migrate.py           Run pending migrations
  python db/migrate.py --fresh   Drop all tables, re-run all migrations
  python db/migrate.py --status  Show migration status
  python db/migrate.py --rollback Rollback last migration
        """,
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Drop all tables and re-run all migrations",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show migration status",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback last migration",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompts",
    )

    args = parser.parse_args()

    # Get database URL from settings
    settings = get_settings()
    runner = MigrationRunner(settings.database_url)

    try:
        await runner.connect()

        if args.status:
            await runner.show_status()
        elif args.fresh:
            await runner.run_fresh(force=args.yes)
        elif args.rollback:
            await runner.rollback_last()
        else:
            await runner.run_pending()

    except asyncpg.InvalidCatalogNameError:
        print("Error: Database does not exist.")
        print("Create it with: createdb <database_name>")
        sys.exit(1)
    except asyncpg.InvalidPasswordError:
        print("Error: Invalid database password.")
        sys.exit(1)
    except ConnectionRefusedError:
        print("Error: Could not connect to database.")
        print("Make sure PostgreSQL is running.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())

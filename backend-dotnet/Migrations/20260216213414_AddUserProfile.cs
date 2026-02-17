using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace backend_dotnet.Migrations
{
    /// <inheritdoc />
    public partial class AddUserProfile : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Explicitly cast existing text columns to uuid for PostgreSQL
            migrationBuilder.Sql("ALTER TABLE \"Documents\" ALTER COLUMN \"UserId\" TYPE uuid USING \"UserId\"::uuid;");
            
            migrationBuilder.Sql("ALTER TABLE \"AspNetUserTokens\" ALTER COLUMN \"UserId\" TYPE uuid USING \"UserId\"::uuid;");
            
            // For primary keys referenced by foreign keys, we might need to handle constraints.
            // But let's try the direct cast first as per the error message.
            migrationBuilder.Sql("ALTER TABLE \"AspNetUsers\" ALTER COLUMN \"Id\" TYPE uuid USING \"Id\"::uuid;");
            
            migrationBuilder.Sql("ALTER TABLE \"AspNetUserRoles\" ALTER COLUMN \"RoleId\" TYPE uuid USING \"RoleId\"::uuid;");
            migrationBuilder.Sql("ALTER TABLE \"AspNetUserRoles\" ALTER COLUMN \"UserId\" TYPE uuid USING \"UserId\"::uuid;");
            
            migrationBuilder.Sql("ALTER TABLE \"AspNetUserLogins\" ALTER COLUMN \"UserId\" TYPE uuid USING \"UserId\"::uuid;");
            
            migrationBuilder.Sql("ALTER TABLE \"AspNetUserClaims\" ALTER COLUMN \"UserId\" TYPE uuid USING \"UserId\"::uuid;");
            
            migrationBuilder.Sql("ALTER TABLE \"AspNetRoles\" ALTER COLUMN \"Id\" TYPE uuid USING \"Id\"::uuid;");
            
            migrationBuilder.Sql("ALTER TABLE \"AspNetRoleClaims\" ALTER COLUMN \"RoleId\" TYPE uuid USING \"RoleId\"::uuid;");

            migrationBuilder.CreateTable(
                name: "UserProfiles",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    FirstName = table.Column<string>(type: "text", nullable: false),
                    LastName = table.Column<string>(type: "text", nullable: false),
                    Address = table.Column<string>(type: "text", nullable: false),
                    DateOfBirth = table.Column<DateOnly>(type: "date", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_UserProfiles", x => x.Id);
                    table.ForeignKey(
                        name: "FK_UserProfiles_AspNetUsers_Id",
                        column: x => x.Id,
                        principalTable: "AspNetUsers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "UserProfiles");

            migrationBuilder.AlterColumn<string>(
                name: "UserId",
                table: "Documents",
                type: "text",
                nullable: false,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<string>(
                name: "UserId",
                table: "AspNetUserTokens",
                type: "text",
                nullable: false,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<string>(
                name: "Id",
                table: "AspNetUsers",
                type: "text",
                nullable: false,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<string>(
                name: "RoleId",
                table: "AspNetUserRoles",
                type: "text",
                nullable: false,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<string>(
                name: "UserId",
                table: "AspNetUserRoles",
                type: "text",
                nullable: false,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<string>(
                name: "UserId",
                table: "AspNetUserLogins",
                type: "text",
                nullable: false,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<string>(
                name: "UserId",
                table: "AspNetUserClaims",
                type: "text",
                nullable: false,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<string>(
                name: "Id",
                table: "AspNetRoles",
                type: "text",
                nullable: false,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<string>(
                name: "RoleId",
                table: "AspNetRoleClaims",
                type: "text",
                nullable: false,
                oldClrType: typeof(Guid),
                oldType: "uuid");
        }
    }
}

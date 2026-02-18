using backend_dotnet.Data;
using backend_dotnet.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
using System.Security.Claims;

namespace backend_dotnet.Endpoints;

public record UserProfileResponse(string FirstName, string LastName, string Email, string Address, DateOnly DateOfBirth);
public record UpdateProfileRequest(string FirstName, string LastName, string Address, DateOnly DateOfBirth);

public static class ProfileEndpoints
{
    public static void MapProfileEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/profile").RequireAuthorization();

        group.MapGet("/", async (ClaimsPrincipal user, AppDbContext db) =>
        {
            var userIdString = user.FindFirstValue(ClaimTypes.NameIdentifier);
            if (!Guid.TryParse(userIdString, out var userId)) return Results.Unauthorized();

            var dbUser = await db.Users.Include(u => u.Profile)
                                       .FirstOrDefaultAsync(u => u.Id == userId);

            if (dbUser == null) return Results.Unauthorized();
            if (dbUser.Profile == null) return Results.NotFound("Profile not found");

            return Results.Ok(new UserProfileResponse(
                dbUser.Profile.FirstName,
                dbUser.Profile.LastName,
                dbUser.Email!,
                dbUser.Profile.Address,
                dbUser.Profile.DateOfBirth
            ));
        });

        group.MapPut("/", async (UpdateProfileRequest request, ClaimsPrincipal user, AppDbContext db) =>
        {
            var userIdString = user.FindFirstValue(ClaimTypes.NameIdentifier);
            if (!Guid.TryParse(userIdString, out var userId)) return Results.Unauthorized();

            var dbUser = await db.Users.Include(u => u.Profile)
                                       .FirstOrDefaultAsync(u => u.Id == userId);

            if (dbUser == null) return Results.Unauthorized();
            
            if (dbUser.Profile == null)
            {
                 dbUser.Profile = new UserProfile 
                 { 
                     Id = userId,
                     FirstName = request.FirstName, 
                     LastName = request.LastName, 
                     Address = request.Address, 
                     DateOfBirth = request.DateOfBirth,
                     User = dbUser
                 };
                 db.UserProfiles.Add(dbUser.Profile);
            }
            else 
            {
                dbUser.Profile.FirstName = request.FirstName;
                dbUser.Profile.LastName = request.LastName;
                dbUser.Profile.Address = request.Address;
                dbUser.Profile.DateOfBirth = request.DateOfBirth;
            }

            await db.SaveChangesAsync();
            return Results.Ok(new { Message = "Profile updated" });
        });
    }
}

using backend_dotnet.Data;
using backend_dotnet.Models;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using System.ComponentModel.DataAnnotations;

namespace backend_dotnet.Endpoints;

public record RegisterExtendedRequest(
    [Required] string Email,
    [Required] string Password,
    [Required] string FirstName,
    [Required] string LastName,
    [Required] string Address,
    [Required] DateOnly DateOfBirth
);

public static class AuthEndpoints
{
    public static void MapAuthEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/auth");

        group.MapPost("/register-extended", async (
            RegisterExtendedRequest request,
            UserManager<User> userManager,
            IUserStore<User> userStore,
            AppDbContext dbContext) =>
        {
            using var transaction = await dbContext.Database.BeginTransactionAsync();

            try
            {
                var user = new User();
                await userStore.SetUserNameAsync(user, request.Email, CancellationToken.None);
                var emailStore = (IUserEmailStore<User>)userStore;
                await emailStore.SetEmailAsync(user, request.Email, CancellationToken.None);

                var result = await userManager.CreateAsync(user, request.Password);

                if (!result.Succeeded)
                {
                    return Results.ValidationProblem(result.Errors.ToDictionary(e => e.Code, e => new[] { e.Description }));
                }

                var profile = new UserProfile
                {
                    Id = user.Id,
                    FirstName = request.FirstName,
                    LastName = request.LastName,
                    Address = request.Address,
                    DateOfBirth = request.DateOfBirth,
                    User = user
                };

                dbContext.UserProfiles.Add(profile);
                await dbContext.SaveChangesAsync();

                await transaction.CommitAsync();

                return Results.Ok(new { UserId = user.Id, Message = "User registered with profile." });
            }
            catch (Exception ex)
            {
                await transaction.RollbackAsync();
                return Results.Problem($"Registration failed: {ex.Message}");
            }
        });
    }
}

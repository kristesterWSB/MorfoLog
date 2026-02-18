using Microsoft.AspNetCore.Identity;

namespace backend_dotnet.Models;

public class User : IdentityUser<Guid>
{
    public virtual UserProfile? Profile { get; set; }
}

# Answers to Hatchway Questions

## Question 1
1. What database changes would be required to the starter code to allow for different roles for authors of a blog post? Imagine that we’d want to also be able to add custom roles and change the permission sets for certain roles on the fly without any code changes.
A: You'd need to make a new table for roles, where each entry had a role name, and permissions for that role. You would then need to add a new attribute / sql column to UserPosts
    definining a role for each UserPost. To implement having at least one owner for each Post, you can either add an additional attribute to Posts counting the number of owners and
    updating this number every time an owner is added or removed from the post, or you could do a nested select statement of "post=PostID AND role=owner" to get the number of owners for each post.
    To add a custom role you would add a new entry to the role table. To change the permission set for a certain role, you'd just update the permission in the role table.


1. How would you have to change the PATCH route given your answer above to handle roles?
A: You would have to add role guards to check if the user has the correct role to modify the post. You would need to add a check for edit privileges for editing the blog post and a different check for being an owner to edit the authors list.
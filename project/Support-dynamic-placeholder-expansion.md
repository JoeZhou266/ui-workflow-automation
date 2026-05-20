Implement dynamic placeholder expansion in json_loader.py Python JSON workflow loader.

Goal:
When loading workflow/tabs/pages/sections/elements from JSON, if an element value
contains a placeholder like ${sin_number}, ${first_name}, ${last_name}, etc.,
the loader should call a corresponding Python function to generate the value
instead of using the literal string.

Requirements:
1. Add a registry/dictionary mapping placeholder names to generator functions.
   Example:
       {
           "sin_number": generate_sin_number,
           "first_name": generate_first_name,
           "last_name": generate_last_name
       }

2. Implement a function `resolve_dynamic_value(value: str)`:
   - Detect patterns like ${placeholder}
   - Look up the placeholder in the registry
   - Call the generator function
   - Return the generated value
   - If no placeholder exists, return the original value

3. Modify the JSON loader so that whenever it reads an element value,
   it passes it through `resolve_dynamic_value()`.

4. Implement example generator functions:
   - generate_sin_number(): return a valid random Canadian SIN
   - generate_first_name(): return a random first name
   - generate_last_name(): return a random last name

5. No rush to update code, provide plan first.

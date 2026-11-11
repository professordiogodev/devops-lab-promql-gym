# Submission

Fork URL: <!-- paste the URL of your fork here -->

## Files to commit

- [ ] `queries.yaml`: your twelve PromQL expressions

## Questions

Answer in your own words. Where a question asks for output, paste it in a code block.

### Q1. Paste your answers to questions 1 and 3 and explain, in your own words, what `rate()` computes and why you give it a range (`[5m]`). What happens to `rate()` when a counter resets (a container restart)?

**Your answer:**

<!-- replace this line with your answer -->

### Q2. Why is `histogram_quantile(0.95, ...)` applied to `sum by (le, service) (rate(..._bucket[5m]))` and not to the raw buckets, and not to an average? What is wrong with averaging percentiles of several instances?

**Your answer:**

<!-- replace this line with your answer -->

### Q3. Paste your query for the error ratio and say why a ratio of two `rate()`s is better than a ratio of two `increase()`s over a short window, and what happens to it when traffic is almost zero.

**Your answer:**

<!-- replace this line with your answer -->

### Q4. Question 9 asks when the orders service would run out of memory. State what `predict_linear` assumes about the future. Name one thing that makes this prediction wrong in real life.

**Your answer:**

<!-- replace this line with your answer -->

### Q5. Name three things that went wrong that night (service, time, size) using only what your queries showed. Which single query would you turn into an alert, and with which `for:`?

**Your answer:**

<!-- replace this line with your answer -->

### Q6. What is the difference between an instant vector, a range vector and a scalar? Give an example of each from your twelve queries.

**Your answer:**

<!-- replace this line with your answer -->

### Q7. Paste the output of `./verify.sh`. It must end with **ALL CHECKS PASSED**.

**Your answer:**

<!-- replace this line with your answer -->

### Q8. **Tear down.** Paste the output of `./verify-teardown.sh`. It must end with **TEARDOWN VERIFIED**.

**Your answer:**

<!-- replace this line with your answer -->

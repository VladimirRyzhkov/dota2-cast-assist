# Roadmap

### App
- [ ] Add a single-screen HTML page for viewing match trends on charts 
  instead of the current JSON format. [ECharts](https://echarts.apache.org/) 
  seems promising for this task
- [ ] Connect to Redis after the events processor to retrieve live matches.
- [ ] Add a database to store and validate tokens
- [ ] Implement token creation and registration
- [ ] Replace Firestore DB with Redis for live_matches_crawler

### Events Processor
- [ ] ![In Progress][in-progress-badge] Add trend calculation to the events processor 
- [ ] ![In Progress][in-progress-badge] Replace Firestore DB with Redis
- [ ] Update system design diagram after Redis adoption

### Testing
- [ ] Achieve unit test coverage of at least 80% in the app.
- [ ] Create unit tests for the events processor.
- [ ] Enable auto-deployment of the events processor job to Dataflow.

### Kubernetes
- [ ] Add a GitHub Actions workflow to manually perform production rollouts 
using ```kubectl rollout restart deployment```, enabling a prod cut

### Documentation
- [ ] Continue with the [developers](DEVELOPERS.md) guide


See the [open issues](https://github.com/data-mission/dota2-cast-assist/issues) for a full list of proposed features (and known issues).

[Back to README.md](README.md)

[in-progress-badge]: https://img.shields.io/badge/In%20Progress-brightgreen?style=flat-square

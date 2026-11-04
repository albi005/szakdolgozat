#import "@preview/merman:0.5.0": mermaid

#set heading(numbering: "1.")

= Development Environment

== Web Framework

StartSCH is built on the ASP.NET Core web framework developed by Microsoft.

=== ASP.NET Core

=== Blazor

Blazor is

== Client-side JavaScript and CSS

=== Web Components

StartSCH requires small client-side interactions, that Blazor cannot accomplish. Blazor's WebAssembly render-mode requires loading nearly 10 megabytes of WebAssembly code, and the .NET runtime must initialize in the user's browser on each page-load, taking more than 3 seconds in optimal conditions with 1 Gb/s internet, stable \~10ms ping to the server, and a desktop computer. Considering StartSCH needs to be usable in any conditions, including places like trains with spotty internet, WebAssembly wouldn't provide the experience users would expect.

An alternative provided by Blazor is its server-side interactive render-mode, where it uses SignalR to send all user-initiated events to the server, where these events get processed, after which the server sends back updates to the DOM. Server mode causes a small delay between user interactions and results showing up in the UI. This delay is significantly amplified in the conditions detailed above, making server-rendering not an option.

Taking inspiration from more classic websites, StartSCH uses JavaScript for client-side interactions on its commonly used pages.

While JavaScript has seen significant investments in capabilities in recent years, one area it falls behind out of the box is type-safety. Nowadays the industry standard for adding type-safety to JS is the TypeScript (TS) language developed by Microsoft. TS is a superset of JS, adding a type-system and type-annotations to the language, which in turn can be used to type-check the code, surfacing any errors caused by wrong type usage, before the transpiled JS code ever runs in a user's browser.

== Database

StartSCH supports persisting its data in two different relational databases. PostgreSQL is used in the production version, and SQLite is used in development.

=== PostgreSQL

PostgreSQL is a free and open-source relational database system, supporting ACID transactions.

=== SQLite

A common hinderance when trying to contribute to web projects developed at the dormitory is setting up a development environment, with setting up development database causing the most issues. Learning from this, StartSCH supports SQLite as its backing store.

As PostgreSQL requires running it as a different process, to . As SQLite is just a library running as part of the StartSCH server process, it doesn't require any configuration, making setting up a development environment significantly simpler.

SQLite stores all of its data in a single file,

=== Entity Framework Core

==== Migrations

== Security

=== Authentication: OpenID Connect

For authentication, StartSCH relies on an OpenID Connect Identity Provider called AuthSCH that is developed by and for the students of the Schönherz Dormitory. This allows the users to log in using the same account they use at numerous different sites developed at the dormitory. As AuthSCH supports EduID login, StartSCH users can also log in using EduID, by selecting it at the AuthSCH login screen.

== Production Deployment: Kubernetes

The production version of StartSCH is deployed using Kubernetes.

=== Metrics, Logs and Traces: OpenTelemetry

Initially the production environment just logged everything to the console. This caused logs to be lost any time the server's pod was recreated.

OpenTelemetry is a project aiming to standardize telemetry and is quickly turning into the industry standard [cite]. In recent years ASP.NET Core received significant investments into its support for OpenTelemetry [cite].

I decided to set up OpenTelemetry in our cluster. Configuring StartSCH to use it is trivial:

```cs
builder.Services
    .AddOpenTelemetry()
    .UseOtlpExporter()
    .ConfigureResource(resource => resource.AddService("startsch"))
    .WithLogging()
    .WithTracing(tracing => tracing
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
    )
    .WithMetrics(metrics => metrics
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddRuntimeInstrumentation()
        .AddMeter("*")
    );
```

This setup instruments the whole app, including logs, metrics and traces. At run-time, the only configuration it needs is a `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable containing the URL of an OpenTelemetry Collector instance.

OpenTelemetry requires a number of services to be running in our cluster. These services are responsible for storing the telemetry data and making it available for human consumption. I wanted a comprehensive setup, that can be reused by our other apps.

There are all-in-one solutions for telemetry, for example SigNoz [link], but those didn't appear to be as widely used across the industry, as opposed to solutions comprised of multiple projects. The most commonly used tools I found for implementing an OpenTelemetry-compatible stack were the OpenTelemetry Collector Prometheus, Loki, Grafana, and Loki. These cover, in order: relaying this data to the storage backends, storing metrics, storing logs, and letting the user conveniently access the data. For storing traces, Jaeger [?] seemed like the most commonly used project, but I decided on using the trace storage backend developed by the makers of Grafana, Tempo, as it was easier to set up [?].

While Kubernetes was designed to accomodate micro-services like these, it doesn't provide a way to reliably manage them out of the box. For this I decided on setting up a GitOps solution using Argo CD. Argo CD requires storing all of its configuration in a Git repository, and enforces it by overwriting any modifications to Kubernetes resources created by Argo CD.

= The Problem

As a university student, a common problem I face is keeping up with all the news around the university.

= The Model

The core entity types of StartSCH are Events, Posts, Categories, Pages and Interests:

#mermaid("
classDiagram
    class Page
    class Category
    class Event
    class Post
    class Interest

    Page o--> Category
    Category o--> Event
    Category o--> Post
    Category o--> Category
    Event o--> Event
    Event o--> Post
    Interest --> Event
    Interest --> Category
")

Events represent real-life events. Posts represent a piece of news, replacing emails. Pages represent organizations publishing content.

Events can contain other Events. For example, the Schönherz Cup could be a top-level Event, its themed days could be second-level Events and everything else becomes a third-level Event. This way, Users only interested in a single day of the cup can follow only that single day and receive updates only for it.

Posts can either be stand-alone or be attached to an Event. These attachments show up on the Post and can be used to promote a given Event or publish updates about it.

Events and Posts (together referred to as _Articles_) are owned by Pages. Pages can organize Articles into Categories. All Categories have a single Page they belong to.

Collaborations between Pages can be represented by assigning Categories from different Pages to a single Article.

As Pages do not directly contain Articles, all Pages must contain an unnamed Category representing the Page itself. This Category is assigned to Articles that do not belong to any Category.

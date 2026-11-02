// Automatikus hír- és eseményaggregátor webalkalmazás fejlesztése
// Actual thesis content only. Formatting/title-page boilerplate is separate.

= Development Environment

== Web Framework

StartSCH is built on the ASP.NET Core web framework developed by Microsoft for the .NET framework.

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

This setup instruments the whole app, including logs, metrics and traces.

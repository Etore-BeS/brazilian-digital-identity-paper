import inspect
import json


def md(text):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": inspect.cleandoc(text).splitlines(keepends=True),
    }


def code(text):
    src = inspect.cleandoc(text).splitlines(keepends=True)
    if src and not src[-1].endswith("\n"):
        src[-1] += "\n"
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": src,
    }


cells = [
    md("""
        # Brazilian Digital Identity in Celebrity Instagram Comments

        ## Title
        **Manifestations of Brazilian Digital Identity in Instagram Comments on Celebrity Posts: A Mixed-Methods Thematic and Content Analysis**

        ## Abstract
        This notebook analyses 17,287 Instagram comments posted on three celebrity accounts (Bruno Mars, Cristiano Ronaldo / CR7, and Fernanda Torres) to investigate how Brazilian users express national digital identity in informal, cross-cultural interactions. Comments were classified through a hybrid pipeline combining rule-based screening, large-language-model annotation, and human adjudication. We report thematic prevalence, character (affective vs. cognitive), sentiment tone, emoji usage, engagement patterns, and statistical associations between celebrity case and expressive categories. Methodological choices are grounded in established qualitative and quantitative content-analysis traditions.

        ## Introduction to the Analytical Framework
        The study integrates three complementary methodological strands:

        1. **Thematic analysis** guides the inductive coding of identity performances, following Braun & Clarke (2006) and Hsieh & Shannon (2005).
        2. **Quantitative content analysis** provides systematic, replicable counts of category frequencies and associations, following Krippendorff (2018).
        3. **Computational validation** of annotations uses LLM-as-annotator protocols and inter-annotator agreement metrics, following Gilardi et al. (2023), Cohen (1960), and Landis & Koch (1977).

        The concept of *digital identity* is interpreted through the lenses of the imagined audience (Marwick & boyd, 2011) and networked identity (boyd, 2014).
    """),
    code("""
        # Section 2: Setup and configuration
        %matplotlib inline

        import os
        import ast
        from datetime import datetime
        from collections import Counter

        import numpy as np
        import pandas as pd
        import matplotlib
        import matplotlib.pyplot as plt
        import seaborn as sns
        from scipy.stats import chi2_contingency

        # Use a non-interactive backend so exported figures are deterministic
        matplotlib.use("Agg")

        # Visual style
        sns.set_theme(style="whitegrid", context="paper", font_scale=1.1)
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["savefig.dpi"] = 200
        plt.rcParams["figure.figsize"] = (10, 6)

        # Reproducibility note
        RNG_SEED = 42
        np.random.seed(RNG_SEED)

        # Output paths
        FIGURES_DIR = "outputs/figures"
        os.makedirs(FIGURES_DIR, exist_ok=True)
        SUMMARY_PATH = "outputs/aggregates/final_dataset_human.csv"
        DATA_PATH = "outputs/classified_comments_human.csv"

        print("Environment ready. Timestamp:", datetime.utcnow().isoformat())
    """),
    md("""
        ## 3. Data Loading
        The source file `outputs/classified_comments_human.csv` merges automated classifications with human-reviewed adjudications. It is the authoritative dataset for all downstream analyses.
    """),
    code("""
        # Section 3: Load dataset
        df = pd.read_csv(DATA_PATH, low_memory=False)

        # Standardise string columns for safer joins and displays
        df["case"] = df["case"].astype(str)

        print("Dataset shape:", df.shape)
        print("Columns:", len(df.columns))
        display(df.head(3))
    """),
    md("""
        ## 4. Data Integrity Checks
        Before analysis, we verify identifiers, review status, and missingness. Replicability in content analysis depends on transparent data-quality checks (Krippendorff, 2018).

        - [Braun & Clarke, 2006](https://doi.org/10.1191/1478088706qp063oa)
        - [Krippendorff, 2018](https://doi.org/10.4135/9781071878781)
    """),
    code("""
        # Section 4: Data integrity
        print("=" * 60)
        print("hash_id uniqueness")
        print("=" * 60)
        n_total = len(df)
        n_unique = df["hash_id"].nunique()
        print(f"Total rows: {n_total}")
        print(f"Unique hash_ids: {n_unique}")
        print(f"Duplicates: {n_total - n_unique}")
        if n_total != n_unique:
            print("Duplicate hash_ids:")
            print(df["hash_id"][df["hash_id"].duplicated(keep=False)].unique())

        print("\n" + "=" * 60)
        print("Classification source counts")
        print("=" * 60)
        print(df["classification_source"].value_counts(dropna=False))

        print("\n" + "=" * 60)
        print("Human review status")
        print("=" * 60)
        print(df["human_reviewed"].value_counts(dropna=False))

        print("\n" + "=" * 60)
        print("Missing values per column (top 15)")
        print("=" * 60)
        missing = df.isna().sum().sort_values(ascending=False)
        print(missing[missing > 0].head(15))
    """),
    md("""
        ## 5. Descriptive Overview
        We first characterise the corpus by celebrity case and engagement (likes). Understanding the distributional shape of engagement is essential before modelling sentiment or theme effects (Pang & Lee, 2008).

        - [Pang & Lee, 2008](https://doi.org/10.1561/1500000011)
    """),
    code("""
        # Section 5: Descriptive overview
        case_counts = df["case"].value_counts().rename_axis("case").reset_index(name="n_comments")
        case_counts["pct"] = 100 * case_counts["n_comments"] / case_counts["n_comments"].sum()
        print("Comments per case:")
        display(case_counts)

        likes_summary = df.groupby("case")["likes"].agg(["count", "mean", "median", "std", "min", "max"]).round(2)
        print("\nLikes distribution by case:")
        display(likes_summary)

        # Histogram of likes (log-scaled count axis because of strong skew)
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.histplot(data=df, x="likes", hue="case", bins=60, kde=False, ax=ax, palette="viridis")
        ax.set_xlabel("Likes")
        ax.set_ylabel("Number of comments")
        ax.set_title("Distribution of likes per comment by celebrity case")
        ax.set_yscale("log")
        ax.legend(title="Case")
        plt.tight_layout()
        hist_path = os.path.join(FIGURES_DIR, "likes_distribution.png")
        plt.savefig(hist_path, bbox_inches="tight")
        print(f"Saved figure: {hist_path}")
        plt.show()
    """),
    md("""
        ## 6. Thematic Analysis Results
        Themes follow a deductive coding frame operationalised after an initial familiarisation phase (Braun & Clarke, 2006). Percentages are computed *within* each celebrity case so that differences in corpus size do not distort comparisons. The six codes are:

        - **C1** Nacionalismo/Orgulho
        - **C2** Humor/Sátira/Meme
        - **C3** Conflito/Rivalidade
        - **C4** Validação/Afeto pelo Estrangeiro
        - **C5** Apropriação do Espaço Digital
        - **NA** Não se aplica / não identificável

        - [Braun & Clarke, 2006](https://doi.org/10.1191/1478088706qp063oa)
        - [Hsieh & Shannon, 2005](https://doi.org/10.1177/1049732305276687)
    """),
    code("""
        # Section 6: Thematic analysis results
        theme_cols = ["theme_C1", "theme_C2", "theme_C3", "theme_C4", "theme_C5", "theme_NA"]
        theme_labels = {
            "theme_C1": "C1: Nacionalismo/Orgulho",
            "theme_C2": "C2: Humor/Sátira/Meme",
            "theme_C3": "C3: Conflito/Rivalidade",
            "theme_C4": "C4: Validação/Afeto pelo Estrangeiro",
            "theme_C5": "C5: Apropriação do Espaço Digital",
            "theme_NA": "N.A.",
        }

        # Counts per case
        theme_counts = df.groupby("case")[theme_cols].sum().T
        theme_counts.index = [theme_labels[c] for c in theme_counts.index]

        # Row percentages (percentage of each case total)
        case_totals = df["case"].value_counts()
        theme_pct = theme_counts.div(case_totals, axis=1) * 100

        print("Theme counts per case:")
        display(theme_counts.round(0).astype(int))
        print("\nTheme percentages per case (row % of case total):")
        display(theme_pct.round(1))

        # Stacked bar plot (percentages)
        fig, ax = plt.subplots(figsize=(10, 6))
        theme_pct.T.plot(kind="bar", stacked=True, ax=ax, colormap="tab10", width=0.7)
        ax.set_ylabel("Percentage of comments in case")
        ax.set_xlabel("Celebrity case")
        ax.set_title("Thematic composition by celebrity case")
        ax.legend(title="Theme", bbox_to_anchor=(1.05, 1), loc="upper left")
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        plt.tight_layout()
        stacked_path = os.path.join(FIGURES_DIR, "theme_stacked_bar.png")
        plt.savefig(stacked_path, bbox_inches="tight")
        print(f"Saved figure: {stacked_path}")
        plt.show()

        # Heatmap of percentages
        fig, ax = plt.subplots(figsize=(9, 6))
        sns.heatmap(theme_pct, annot=True, fmt=".1f", cmap="YlGnBu", cbar_kws={"label": "% of case"}, ax=ax)
        ax.set_title("Theme prevalence heatmap (% within case)")
        ax.set_xlabel("Celebrity case")
        ax.set_ylabel("Theme")
        plt.tight_layout()
        heatmap_path = os.path.join(FIGURES_DIR, "theme_heatmap.png")
        plt.savefig(heatmap_path, bbox_inches="tight")
        print(f"Saved figure: {heatmap_path}")
        plt.show()
    """),
    md("""
        ## 7. Character and Tone Analysis
        Each comment is assigned a **character** (Afetivo / Cognitivo) and a **tone** (Positivo / Neutro / Negativo). Affective/cognitive framing captures whether identity is performed emotionally or argumentatively, consistent with research on imagined audiences and networked self-presentation (Marwick & boyd, 2011; boyd, 2014). Sentiment tone follows standard opinion-mining conventions (Pang & Lee, 2008).

        - [Pang & Lee, 2008](https://doi.org/10.1561/1500000011)
        - [Marwick & boyd, 2011](https://doi.org/10.1177/1461444810365313)
        - [boyd, 2014](https://yalebooks.yale.edu/book/9780300166316/its-complicated)
    """),
    code("""
        # Section 7: Character and tone analysis
        # Character crosstab (row percentages within case)
        char_crosstab = pd.crosstab(df["case"], df["character"], normalize="index") * 100
        print("Character by case (% within case):")
        display(char_crosstab.round(1))

        # Tone crosstab (row percentages within case)
        tone_crosstab = pd.crosstab(df["case"], df["tone"], normalize="index") * 100
        print("\nTone by case (% within case):")
        display(tone_crosstab.round(1))

        # Grouped bar plot: character
        fig, ax = plt.subplots(figsize=(8, 5))
        char_crosstab.plot(kind="bar", ax=ax, color=["#4c78a8", "#f58518"], width=0.7)
        ax.set_ylabel("Percentage of comments in case")
        ax.set_xlabel("Celebrity case")
        ax.set_title("Character (affective vs. cognitive) by case")
        ax.legend(title="Character")
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        plt.tight_layout()
        char_path = os.path.join(FIGURES_DIR, "character_by_case.png")
        plt.savefig(char_path, bbox_inches="tight")
        print(f"Saved figure: {char_path}")
        plt.show()

        # Grouped bar plot: tone
        fig, ax = plt.subplots(figsize=(9, 5))
        tone_crosstab.plot(kind="bar", ax=ax, color=["#e45756", "#f58518", "#54a24b"], width=0.7)
        ax.set_ylabel("Percentage of comments in case")
        ax.set_xlabel("Celebrity case")
        ax.set_title("Tone (sentiment) by case")
        ax.legend(title="Tone")
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        plt.tight_layout()
        tone_path = os.path.join(FIGURES_DIR, "tone_by_case.png")
        plt.savefig(tone_path, bbox_inches="tight")
        print(f"Saved figure: {tone_path}")
        plt.show()
    """),
    md("""
        ## 8. Statistical Testing
        We test the null hypothesis that expressive category (theme, character, tone) is independent of celebrity case using Pearson's chi-square test of independence (Krippendorff, 2018). Effect size is reported with Cramér's V, derived from the chi-square statistic (Cramér, 1946). For inter-annotator reliability we report Cohen's kappa (Cohen, 1960; Landis & Koch, 1977).

        - [Krippendorff, 2018](https://doi.org/10.4135/9781071878781)
        - [Cohen, 1960](https://doi.org/10.1177/001316446002000104)
        - [Landis & Koch, 1977](https://doi.org/10.2307/2529310)
        - [Cramér, 1946](https://en.wikipedia.org/wiki/Cram%C3%A9r%27s_V) (original monograph; V implemented from chi-square)
    """),
    code('''
        # Section 8: Statistical testing
        def cramers_v(chi2, n, r, k):
            """Return Cramér's V for an r x k contingency table."""
            return np.sqrt(chi2 / (n * (min(r, k) - 1)))

        def chi_square_test(variable):
            """Run chi-square test of independence between case and variable."""
            table = pd.crosstab(df["case"], df[variable])
            chi2, p, dof, expected = chi2_contingency(table)
            n = table.sum().sum()
            v = cramers_v(chi2, n, table.shape[0], table.shape[1])
            return {
                "variable": variable,
                "chi2": chi2,
                "df": dof,
                "p_value": p,
                "cramers_v": v,
                "n": n,
                "min_expected": expected.min(),
            }

        test_vars = theme_cols + ["character", "tone"]
        test_results = [chi_square_test(v) for v in test_vars]
        results_df = pd.DataFrame(test_results)

        # Benjamini-Hochberg FDR correction for multiple comparisons across themes
        from scipy.stats import false_discovery_rate

        # Fallback if scipy version does not expose false_discovery_rate
        try:
            _, fdr_p = false_discovery_rate(results_df["p_value"].values)
        except Exception:
            # Manual Benjamini-Hochberg
            pvals = results_df["p_value"].values
            order = np.argsort(pvals)
            ranks = np.empty_like(order)
            ranks[order] = np.arange(1, len(pvals) + 1)
            fdr_p = pvals * len(pvals) / ranks
            fdr_p = np.minimum.accumulate(fdr_p[np.argsort(order)])

        results_df["fdr_p_value"] = fdr_p
        print("Chi-square tests of independence (case × variable):")
        display(results_df[["variable", "chi2", "df", "p_value", "fdr_p_value", "cramers_v", "n"]].round(4))

        # Cramér's V interpretation (Cohen-style conventions for V)
        def interpret_v(v):
            if v < 0.10:
                return "negligible"
            elif v < 0.30:
                return "small"
            elif v < 0.50:
                return "medium"
            else:
                return "large"

        results_df["effect_size"] = results_df["cramers_v"].apply(interpret_v)
        print("\nEffect-size interpretation:")
        display(results_df[["variable", "cramers_v", "effect_size"]])
    '''),
    md("""
        ## 9. Human Review Impact
        A subset of comments was flagged for human review because the two LLM annotators disagreed. Adjudication followed a validated LLM-as-annotator workflow in which human reviewers override machine labels when necessary (Gilardi et al., 2023). We compare the final adjudicated labels with the two pre-adjudication coder outputs and report agreement using Cohen's kappa (Cohen, 1960; Landis & Koch, 1977).

        - [Gilardi et al., 2023](https://doi.org/10.1073/pnas.2305016120)
        - [Cohen, 1960](https://doi.org/10.1177/001316446002000104)
        - [Landis & Koch, 1977](https://doi.org/10.2307/2529310)
    """),
    code('''
        # Section 9: Human review impact
        print("=" * 60)
        print("Classification source counts")
        print("=" * 60)
        source_counts = df["classification_source"].value_counts(dropna=False)
        display(source_counts.to_frame("n"))

        reviewed = df[df["human_reviewed"] == True].copy()
        print(f"\nHuman-reviewed rows: {len(reviewed)} ({100*len(reviewed)/len(df):.2f}% of corpus)")

        # Convert human theme columns to boolean for safe comparison
        human_theme_cols = [c + "_human" for c in theme_cols]
        for c in human_theme_cols:
            reviewed[c] = reviewed[c].fillna(False).astype(bool)

        # For reviewed rows, compare final theme with coder A and coder B
        coder_a_cols = ["theme_C1_a", "theme_C2_a", "theme_C3_a", "theme_C4_a", "theme_C5_a", "theme_NA_a"]
        coder_b_cols = ["theme_C1_b", "theme_C2_b", "theme_C3_b", "theme_C4_b", "theme_C5_b", "theme_NA_b"]

        # Some coder columns may be stored as object; coerce to bool
        for c in coder_a_cols + coder_b_cols:
            reviewed[c] = reviewed[c].fillna(False).astype(bool)

        def cohen_kappa(a, b):
            """Compute Cohen's kappa for two binary series of equal length."""
            a = a.astype(int)
            b = b.astype(int)
            n = len(a)
            p_o = (a == b).mean()
            p_a1 = a.mean()
            p_b1 = b.mean()
            p_e = p_a1 * p_b1 + (1 - p_a1) * (1 - p_b1)
            return np.nan if p_e == 1 else (p_o - p_e) / (1 - p_e)

        agreement_rows = []
        for final_col, a_col, b_col, label in zip(theme_cols, coder_a_cols, coder_b_cols, theme_labels.values()):
            agreement_a = (reviewed[final_col] == reviewed[a_col]).mean()
            agreement_b = (reviewed[final_col] == reviewed[b_col]).mean()
            kappa_a = cohen_kappa(reviewed[final_col], reviewed[a_col])
            kappa_b = cohen_kappa(reviewed[final_col], reviewed[b_col])
            kappa_ab = cohen_kappa(reviewed[a_col], reviewed[b_col])
            agreement_rows.append({
                "theme": label,
                "n_reviewed": len(reviewed),
                "agree_final_vs_A": agreement_a,
                "agree_final_vs_B": agreement_b,
                "kappa_final_vs_A": kappa_a,
                "kappa_final_vs_B": kappa_b,
                "kappa_A_vs_B": kappa_ab,
            })

        agreement_df = pd.DataFrame(agreement_rows)
        print("\nAdjudication agreement for human-reviewed rows:")
        display(agreement_df.round(3))

        # Theme prevalence before (average of A and B) vs after adjudication
        prev_after = reviewed[theme_cols].mean() * 100
        prev_before = (reviewed[coder_a_cols].mean() + reviewed[coder_b_cols].mean()) / 2 * 100
        prev_compare = pd.DataFrame({
            "theme": [theme_labels[c] for c in theme_cols],
            "before_avg_pct": prev_before.values,
            "after_pct": prev_after.values,
        })
        prev_compare["delta_pct"] = prev_compare["after_pct"] - prev_compare["before_avg_pct"]
        print("\nTheme prevalence before vs. after adjudication (% of reviewed rows):")
        display(prev_compare.round(2))
    '''),
    md("""
        ## 10. Emoji and Engagement Exploratory Analysis
        Emoji are a central paralinguistic resource through which users signal identity and affect in networked publics (Marwick & boyd, 2011; boyd, 2014). We parse the `emojis_list` column and relate emoji presence and theme to likes, a proxy for engagement (Pang & Lee, 2008).

        - [Marwick & boyd, 2011](https://doi.org/10.1177/1461444810365313)
        - [boyd, 2014](https://yalebooks.yale.edu/book/9780300166316/its-complicated)
        - [Pang & Lee, 2008](https://doi.org/10.1561/1500000011)
    """),
    code('''
        # Section 10: Emoji and engagement exploratory analysis
        def parse_emojis(cell):
            """Parse the string representation of an emoji list into a Python list."""
            if pd.isna(cell):
                return []
            try:
                return ast.literal_eval(cell)
            except (ValueError, SyntaxError):
                return []

        df["emojis_parsed"] = df["emojis_list"].apply(parse_emojis)
        df["n_emojis"] = df["emojis_parsed"].apply(len)

        # Top emojis per case
        top_n = 10
        emoji_tables = {}
        for case in sorted(df["case"].unique()):
            emojis = [e for sublist in df.loc[df["case"] == case, "emojis_parsed"] for e in sublist]
            counter = Counter(emojis)
            top = counter.most_common(top_n)
            emoji_tables[case] = pd.DataFrame(top, columns=["emoji", "count"])
            print(f"\nTop {top_n} emojis for {case}:")
            display(emoji_tables[case])

        # Emoji engagement: average likes by number-of-emojis bins
        df["emoji_bin"] = pd.cut(df["n_emojis"], bins=[-0.1, 0, 1, 2, 5, 100], labels=["0", "1", "2", "3-5", "6+"])
        engagement = df.groupby(["case", "emoji_bin"])["likes"].agg(["mean", "median", "count"]).reset_index()
        print("\nEngagement by emoji count bin:")
        display(engagement.round(2))

        # Likes by theme (melted; comments can contribute to multiple themes)
        melted = df.melt(id_vars=["case", "likes"], value_vars=theme_cols, var_name="theme_code", value_name="present")
        melted = melted[melted["present"]].copy()
        melted["theme"] = melted["theme_code"].map(theme_labels)

        fig, ax = plt.subplots(figsize=(12, 6))
        sns.boxplot(data=melted, x="theme", y="likes", hue="case", ax=ax, palette="viridis", showfliers=False)
        ax.set_yscale("log")
        ax.set_ylabel("Likes (log scale)")
        ax.set_xlabel("Theme")
        ax.set_title("Engagement (likes) distribution by theme and case")
        ax.tick_params(axis="x", rotation=30)
        ax.legend(title="Case", bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.tight_layout()
        likes_theme_path = os.path.join(FIGURES_DIR, "likes_by_theme.png")
        plt.savefig(likes_theme_path, bbox_inches="tight")
        print(f"Saved figure: {likes_theme_path}")
        plt.show()

        # Median likes per theme (across all cases)
        median_likes_theme = melted.groupby("theme")["likes"].median().sort_values(ascending=False)
        print("\nMedian likes by theme (comments flagged with that theme):")
        display(median_likes_theme.round(2))
    '''),
    md("""
        ## 11. Summary Table Generation
        The following table reproduces the structure of `outputs/aggregates/final_dataset_human.csv`, the paper's main quantitative summary. It reports counts and within-case percentages for themes, character, and tone.
    """),
    code("""
        # Section 11: Summary table generation
        cases = ["Bruno_Mars", "CR7", "Fernanda_Torres"]

        summary_rows = []

        # Themes
        for col, label in theme_labels.items():
            row = {"Dimensão": "TEMA", "Categoria": label}
            total = 0
            for case in cases:
                n = int((df.loc[df["case"] == case, col] == True).sum())
                pct = 100 * n / len(df[df["case"] == case])
                row[f"{case}_N"] = n
                row[f"{case}_%"] = f"{pct:.1f}%"
                total += n
            row["Total_N"] = total
            summary_rows.append(row)

        # Character
        for char in ["Afetivo", "Cognitivo"]:
            row = {"Dimensão": "CARÁTER", "Categoria": char}
            total = 0
            for case in cases:
                n = int((df.loc[df["case"] == case, "character"] == char).sum())
                pct = 100 * n / len(df[df["case"] == case])
                row[f"{case}_N"] = n
                row[f"{case}_%"] = f"{pct:.1f}%"
                total += n
            row["Total_N"] = total
            summary_rows.append(row)
        # Character total row
        row = {"Dimensão": "CARÁTER", "Categoria": "Total"}
        for case in cases:
            n = len(df[df["case"] == case])
            row[f"{case}_N"] = n
            row[f"{case}_%"] = np.nan
        row["Total_N"] = len(df)
        summary_rows.append(row)

        # Tone
        for tone in ["Negativo", "Neutro", "Positivo"]:
            row = {"Dimensão": "TOM (SENTIMENTO)", "Categoria": tone}
            total = 0
            for case in cases:
                n = int((df.loc[df["case"] == case, "tone"] == tone).sum())
                pct = 100 * n / len(df[df["case"] == case])
                row[f"{case}_N"] = n
                row[f"{case}_%"] = f"{pct:.1f}%"
                total += n
            row["Total_N"] = total
            summary_rows.append(row)
        # Tone total row
        row = {"Dimensão": "TOM (SENTIMENTO)", "Categoria": "Total"}
        for case in cases:
            n = len(df[df["case"] == case])
            row[f"{case}_N"] = n
            row[f"{case}_%"] = np.nan
        row["Total_N"] = len(df)
        summary_rows.append(row)

        summary_table = pd.DataFrame(summary_rows)
        summary_table.to_csv(SUMMARY_PATH, index=False)
        print(f"Saved summary table: {SUMMARY_PATH}")
        display(summary_table)
    """),
    md("""
        ## 12. References

        1. Braun, V., & Clarke, V. (2006). Using thematic analysis in psychology. *Qualitative Research in Psychology*, 3(2), 77–101. https://doi.org/10.1191/1478088706qp063oa
        2. Krippendorff, K. (2018). *Content analysis: An introduction to its methodology* (4th ed.). SAGE. https://doi.org/10.4135/9781071878781
        3. Hsieh, H. F., & Shannon, S. E. (2005). Three approaches to qualitative content analysis. *Qualitative Health Research*, 15(9), 1277–1288. https://doi.org/10.1177/1049732305276687
        4. Gilardi, F., Alizadeh, M., & Kubli, M. (2023). ChatGPT outperforms crowd workers for text-annotation tasks. *PNAS*, 120(30), e2305016120. https://doi.org/10.1073/pnas.2305016120
        5. Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*, 20(1), 37–46. https://doi.org/10.1177/001316446002000104
        6. Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159–174. https://doi.org/10.2307/2529310
        7. Pang, B., & Lee, L. (2008). Opinion mining and sentiment analysis. *Foundations and Trends in Information Retrieval*, 2(1–2), 1–135. https://doi.org/10.1561/1500000011
        8. Marwick, A., & boyd, d. (2011). I tweet honestly, I tweet passionately: Twitter users, context collapse, and the imagined audience. *New Media & Society*, 13(1), 114–133. https://doi.org/10.1177/1461444810365313
        9. boyd, d. (2014). *It's complicated: The social lives of networked teens*. Yale University Press. https://yalebooks.yale.edu/book/9780300166316/its-complicated
        10. Cramér, H. (1946). *Mathematical methods of statistics*. Princeton University Press. (Cramér's V implemented from Pearson's chi-square.)
    """),
]

nb = {
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": ""},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
    "cells": cells,
}

with open("analysis.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Created analysis.ipynb with", len(cells), "cells.")

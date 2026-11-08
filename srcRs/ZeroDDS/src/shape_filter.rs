// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 ZeroDDS Contributors
//! `--cft <expr>` content-filter support for the subscriber side.
//!
//! Wired onto ZeroDDS's **existing** `zerodds-sql-filter` crate
//! (`crates/sql-filter`) and `DataReader::with_filter` builder — no new
//! filter/expression engine. `RowAccess` is implemented for `ShapeType`
//! so a parsed `Expr` (`color = 'RED'`, `x > 100 AND y < 50`, ...) can be
//! evaluated per-sample.
//!
//! This is a vendor extension (mirrors DustDDS's/HDDS's `--cft`, not in
//! the `dds-rtps` README's own flag table); it exists so the harness's
//! `'failed to create content filtered topic'` `pexpect` alternative
//! (subscriber Step 3 in `interoperability_report.py`) has something to
//! trigger against on a malformed expression.

use crate::shape_type::ShapeType;
use zerodds_sql_filter::{RowAccess, Value};

/// `RowAccess` view onto a `ShapeType` sample — maps the SQL-filter
/// field names (`color`, `x`, `y`, `shapesize`) 1:1 onto the struct
/// fields.
struct ShapeRow<'a>(&'a ShapeType);

impl RowAccess for ShapeRow<'_> {
    fn get(&self, path: &str) -> Option<Value> {
        match path {
            "color" => Some(Value::String(self.0.color.clone())),
            "x" => Some(Value::Int(i64::from(self.0.x))),
            "y" => Some(Value::Int(i64::from(self.0.y))),
            "shapesize" => Some(Value::Int(i64::from(self.0.shapesize))),
            _ => None,
        }
    }
}

/// Parses `expr` and returns a `Fn(&ShapeType) -> bool` closure suitable
/// for `DataReader::with_filter`.
///
/// # Errors
/// The `zerodds_sql_filter::ParseError` on a malformed expression — the
/// caller prints `'failed to create content filtered topic'` (the exact
/// harness match string) and skips reader creation.
pub fn compile(expr: &str) -> Result<impl Fn(&ShapeType) -> bool + Send + Sync + 'static, String> {
    let parsed = zerodds_sql_filter::parse(expr).map_err(|e| e.0)?;
    Ok(move |sample: &ShapeType| parsed.evaluate(&ShapeRow(sample), &[]).unwrap_or(false))
}
